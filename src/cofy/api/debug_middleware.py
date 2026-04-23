import io
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

        import yappi  # noqa: PLC0415

        yappi.set_clock_type("wall")
        yappi.start(builtins=False)

        response = await call_next(request)

        yappi.stop()
        buf = io.StringIO()
        yappi.get_thread_stats().print_all(out=buf)
        buf.write("\n")
        yappi.get_func_stats().print_all(
            out=buf,
            columns={0: ("name", 120), 1: ("ncall", 8), 2: ("tsub", 10), 3: ("ttot", 10), 4: ("tavg", 10)},
        )
        (request_dir / "profile.txt").write_text(buf.getvalue(), encoding="utf-8")
        yappi.clear_stats()

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
