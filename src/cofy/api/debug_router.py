import io
import json
import pstats
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse


class DebugRouter(APIRouter):
    """Router exposing debug information captured by DebugMiddleware."""

    def __init__(self, debug_dir: Path) -> None:
        super().__init__(prefix="/debug", tags=["debug"])
        self._debug_dir = debug_dir
        self.add_api_route("/{request_id}/profile", self._get_profile, methods=["GET"])

    def _request_dir(self, request_id: str) -> Path:
        path = self._debug_dir / request_id
        if not path.is_dir():
            raise HTTPException(status_code=404, detail=f"No debug data found for request '{request_id}'")
        return path

    def _read_json(self, path: Path) -> Any:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    async def _get_profile(self, request_id: str) -> PlainTextResponse:
        request_dir = self._request_dir(request_id)
        profile_path = request_dir / "profile.pstat"
        if not profile_path.exists():
            raise HTTPException(
                status_code=404,
                detail="No profile data available. Install yappi to enable profiling.",
            )
        buf = io.StringIO()
        stats = pstats.Stats(str(profile_path), stream=buf)
        stats.sort_stats(pstats.SortKey.CUMULATIVE)
        stats.print_stats()
        return PlainTextResponse(buf.getvalue())
