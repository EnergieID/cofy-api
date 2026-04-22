import json
import logging
import time
import uuid
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = logging.getLogger("uvicorn")


class DebugMiddleware(BaseHTTPMiddleware):
    """Middleware that profiles each request and persists the input, output, and profiling data to disk."""

    def __init__(self, app: ASGIApp, debug_dir: Path, base_url: str = "/debug") -> None:
        super().__init__(app)
        self._debug_dir = debug_dir
        self._base_url = base_url.rstrip("/")

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip debug endpoints themselves to avoid recursion
        if request.url.path.startswith(self._base_url):
            return await call_next(request)

        request_id = str(uuid.uuid4())
        t_start = time.perf_counter()
        request_dir = self._debug_dir / request_id
        request_dir.mkdir(parents=True, exist_ok=True)

        # Buffer request body so it can be read by downstream handlers too
        body_bytes = await request.body()

        async def receive():
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        request = Request(request.scope, receive)

        # Capture request info
        try:
            body_text = body_bytes.decode("utf-8")
            try:
                body_data = json.loads(body_text)
            except (json.JSONDecodeError, ValueError):
                body_data = body_text
        except UnicodeDecodeError:
            body_data = f"<binary {len(body_bytes)} bytes>"

        request_info = {
            "id": request_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": {k: v for k, v in request.headers.items() if k.lower() not in ("authorization", "cookie")},
            "body": body_data,
        }

        # Profile the request
        try:
            from pyinstrument import Profiler  # noqa: PLC0415

            profiler = Profiler(async_mode="enabled")
            profiler.start()
            profiling_available = True
        except ImportError:
            profiler = None
            profiling_available = False

        response = await call_next(request)

        if profiling_available and profiler is not None:
            profiler.stop()
            profile_html = profiler.output_html()
            (request_dir / "profile.html").write_text(profile_html, encoding="utf-8")

        # Buffer response body
        response_body_chunks = []
        async for chunk in response.body_iterator:
            response_body_chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode("utf-8"))
        response_bytes = b"".join(response_body_chunks)

        try:
            response_text = response_bytes.decode("utf-8")
            try:
                response_data = json.loads(response_text)
            except (json.JSONDecodeError, ValueError):
                response_data = response_text
        except UnicodeDecodeError:
            response_data = f"<binary {len(response_bytes)} bytes>"

        response_info = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response_data,
        }

        # Persist to disk
        (request_dir / "request.json").write_text(json.dumps(request_info, indent=2, default=str), encoding="utf-8")
        (request_dir / "response.json").write_text(json.dumps(response_info, indent=2, default=str), encoding="utf-8")

        elapsed_ms = (time.perf_counter() - t_start) * 1000
        logger.info(
            "%s %s → %d  id=%s  %.1fms",
            request_info["method"],
            request_info["path"],
            response.status_code,
            request_id,
            elapsed_ms,
        )

        debug_url = f"{self._base_url}/{request_id}"

        new_headers = dict(response.headers)
        new_headers["X-Debug-Id"] = request_id
        new_headers["X-Debug-Url"] = debug_url

        return Response(
            content=response_bytes,
            status_code=response.status_code,
            headers=new_headers,
            media_type=response.media_type,
        )
