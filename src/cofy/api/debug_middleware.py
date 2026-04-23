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
    """Middleware that profiles each request and persists profiling data to disk."""

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

        from pyinstrument import Profiler  # noqa: PLC0415

        profiler = Profiler(async_mode="enabled")
        profiler.start()

        response = await call_next(request)

        profiler.stop()
        profile_html = profiler.output_html()
        (request_dir / "profile.html").write_text(profile_html, encoding="utf-8")

        elapsed_ms = (time.perf_counter() - t_start) * 1000
        logger.info(
            "%s %s → %d  id=%s  %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            request_id,
            elapsed_ms,
        )

        debug_url = f"{self._base_url}/{request_id}/profile"

        response.headers["X-Debug-Id"] = request_id
        response.headers["X-Debug-Url"] = debug_url

        return response
