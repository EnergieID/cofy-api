import json
import logging
import time
import tracemalloc
import uuid
from pathlib import Path

import memray
from pyinstrument import Profiler
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

        # Start memray first so pyinstrument's setprofile sits on top of it.
        # Teardown must be LIFO: stop pyinstrument before memray exits.
        memray_output = request_dir / "memory.bin"
        profiler = Profiler(async_mode="enabled")
        memray_tracker = memray.Tracker(memray_output)
        memray_tracker.__enter__()

        tracemalloc.start()
        mem_before = tracemalloc.take_snapshot()
        profiler.start()

        response = await call_next(request)

        profiler.stop()  # must happen before memray exits
        mem_after = tracemalloc.take_snapshot()
        tracemalloc.stop()
        memray_tracker.__exit__(None, None, None)

        profile_html = profiler.output_html()
        (request_dir / "profile.html").write_text(profile_html, encoding="utf-8")

        peak_mem_kb = sum(s.size for s in mem_after.statistics("lineno")) / 1024
        mem_stats = mem_after.compare_to(mem_before, "lineno")
        top_allocs = [
            {"file": str(s.traceback[0]) if s.traceback else "?", "size_bytes": s.size_diff, "count_diff": s.count_diff}
            for s in mem_stats[:10]
            if s.size_diff > 0
        ]

        # Buffer response body
        response_body_chunks = []
        async for chunk in response.body_iterator:  # type: ignore[attr-defined]
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

        memory_info = {
            "peak_kb": round(peak_mem_kb, 1),
            "top_allocations": top_allocs,
            "memray_bin": str(memray_output),
        }

        # Persist to disk
        (request_dir / "request.json").write_text(json.dumps(request_info, indent=2, default=str), encoding="utf-8")
        (request_dir / "response.json").write_text(json.dumps(response_info, indent=2, default=str), encoding="utf-8")
        (request_dir / "memory.json").write_text(json.dumps(memory_info, indent=2, default=str), encoding="utf-8")

        elapsed_ms = (time.perf_counter() - t_start) * 1000
        logger.info(
            "%s %s → %d  id=%s  %.1fms  mem=%.1fkb",
            request_info["method"],
            request_info["path"],
            response.status_code,
            request_id,
            elapsed_ms,
            peak_mem_kb,
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
