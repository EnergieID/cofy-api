import json
from pathlib import Path
from typing import Any

import memray
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from memray.reporters.flamegraph import FlameGraphReporter


class DebugRouter(APIRouter):
    """Router exposing debug information captured by DebugMiddleware."""

    def __init__(self, debug_dir: Path) -> None:
        super().__init__(prefix="/debug", tags=["debug"])
        self._debug_dir = debug_dir
        self.add_api_route("/{request_id}", self._get_debug_info, methods=["GET"])
        self.add_api_route("/{request_id}/profile", self._get_profile, methods=["GET"])
        self.add_api_route("/{request_id}/flamegraph", self._get_flamegraph, methods=["GET"])

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
        memory_data = self._read_json(request_dir / "memory.json")
        has_profile = (request_dir / "profile.html").exists()
        has_flamegraph = (request_dir / "memory.bin").exists()

        payload = {
            "request_id": request_id,
            "request": request_data,
            "response": response_data,
            "memory": memory_data,
            "links": {
                "debug": f"/debug/{request_id}",
                **({"profile": f"/debug/{request_id}/profile"} if has_profile else {}),
                **({"flamegraph": f"/debug/{request_id}/flamegraph"} if has_flamegraph else {}),
            },
        }
        return JSONResponse(payload)

    async def _get_profile(self, request_id: str) -> HTMLResponse:
        request_dir = self._request_dir(request_id)
        profile_path = request_dir / "profile.html"
        if not profile_path.exists():
            raise HTTPException(status_code=404, detail="No CPU profile data available.")
        return HTMLResponse(profile_path.read_text(encoding="utf-8"))

    async def _get_flamegraph(self, request_id: str) -> HTMLResponse:
        request_dir = self._request_dir(request_id)
        bin_path = request_dir / "memory.bin"
        if not bin_path.exists():
            raise HTTPException(status_code=404, detail="No memray data available.")
        html_path = request_dir / "flamegraph.html"
        if not html_path.exists():
            # Generate the flamegraph HTML from the binary on first access
            reader = memray.FileReader(str(bin_path))
            reporter = FlameGraphReporter.from_snapshot(
                list(reader.get_high_watermark_allocation_records(merge_threads=True)),
                memory_records=list(reader.get_memory_snapshots()),
                native_traces=reader.metadata.has_native_traces,
            )
            with html_path.open("w", encoding="utf-8") as f:
                reporter.render(
                    outfile=f,
                    metadata=reader.metadata,
                    show_memory_leaks=False,
                    merge_threads=True,
                    inverted=False,
                )
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
