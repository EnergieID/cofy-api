import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse


class DebugRouter(APIRouter):
    """Router exposing debug information captured by DebugMiddleware."""

    def __init__(self, debug_dir: Path) -> None:
        super().__init__(prefix="/debug", tags=["debug"])
        self._debug_dir = debug_dir
        self.add_api_route("/{request_id}", self._get_debug_info, methods=["GET"])
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

    async def _get_debug_info(self, request_id: str) -> JSONResponse:
        request_dir = self._request_dir(request_id)
        request_data = self._read_json(request_dir / "request.json")
        response_data = self._read_json(request_dir / "response.json")
        has_profile = (request_dir / "profile.html").exists()

        payload = {
            "request_id": request_id,
            "request": request_data,
            "response": response_data,
            "links": {
                "debug": f"/debug/{request_id}",
                **({"profile": f"/debug/{request_id}/profile"} if has_profile else {}),
            },
        }
        return JSONResponse(payload)

    async def _get_profile(self, request_id: str) -> HTMLResponse:
        request_dir = self._request_dir(request_id)
        profile_path = request_dir / "profile.html"
        if not profile_path.exists():
            raise HTTPException(
                status_code=404,
                detail="No profile data available. Install pyinstrument to enable profiling.",
            )
        return HTMLResponse(profile_path.read_text(encoding="utf-8"))
