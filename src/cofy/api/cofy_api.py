import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..version import get_installed_version
from .docs_router import DocsRouter
from .from_settings_mixin import BaseSettingsModel, FromSettingsMixin
from .module import Module, ModuleSettings

DEFAULT_ARGS: dict[str, Any] = {
    "title": "Cofy API",
    "version": get_installed_version(),
    "description": "Modular cloud API for energy data",
    "docs_url": None,
    "redoc_url": None,
    "openapi_url": None,
}


class CofyAPISettings(BaseSettingsModel):
    type: str = "cofy_api"
    title: str = DEFAULT_ARGS["title"]
    description: str = DEFAULT_ARGS["description"]
    debug_mode: bool = False
    debug_dir: Path | None = None
    modules: list[ModuleSettings] | None = None


class CofyAPI(FastAPI, FromSettingsMixin, settings=CofyAPISettings):
    def __init__(
        self, *, debug_mode: bool = False, debug_dir: Path | None = None, modules: list[Module] | None = None, **kwargs
    ):
        super().__init__(**(DEFAULT_ARGS | kwargs))
        self._modules: list[Module] = []
        self.include_router(DocsRouter(self.openapi))
        self.add_route("/health", self.health_check, methods=["GET"])

        if debug_mode:
            from .debug_middleware import DebugMiddleware  # noqa: PLC0415
            from .debug_router import DebugRouter  # noqa: PLC0415

            resolved_debug_dir = debug_dir or Path(tempfile.mkdtemp(prefix="cofy_debug_"))
            self.add_middleware(DebugMiddleware, debug_dir=resolved_debug_dir)
            self.include_router(DebugRouter(debug_dir=resolved_debug_dir), include_in_schema=False)

        if modules is not None:
            for module in modules:
                self.register_module(module)

    def openapi(self):
        self.openapi_tags = self.tags_metadata
        schema = super().openapi()
        if self.root_path:
            root_path = self.root_path.rstrip("/")
            server_urls = {s.get("url") for s in schema.get("servers", [])}
            if root_path not in server_urls:
                schema["servers"] = [{"url": root_path}] + schema.get("servers", [])
        return schema

    def register_module(self, module: Module):
        self._modules.append(module)
        self.include_router(module)

    def health_check(self, request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @property
    def tags_metadata(self) -> list[dict[str, Any]]:
        return [module.tag for module in self._modules]

    @property
    def modules(self) -> tuple[Module, ...]:
        return tuple(self._modules)
