import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ConfigDict, model_validator

from .docs_router import DocsRouter
from .from_settings_mixin import BaseSettingsModel, FromSettingsMixin
from .module import Module, ModuleSettings
from .references import check_references, resolving
from .resource import ResourceSettings
from .secret import SecretSettings
from .token_auth import Auth, AuthSettings
from .version import get_installed_version

if TYPE_CHECKING:
    # Published at runtime by finalize(); the base class is the static stand-in.
    AnyModuleSettings = ModuleSettings
    AnyAuthSettings = AuthSettings
    AnyResourceSettings = ResourceSettings

DEFAULT_ARGS: dict[str, Any] = {
    "title": "Cofy API",
    "version": get_installed_version(),
    "description": "Modular cloud API for energy data",
    "docs_url": None,
    "redoc_url": None,
    "openapi_url": None,
}


class CofyAPISettings(BaseSettingsModel):
    # A configuration holds its secrets' values, which a validation error would otherwise quote.
    model_config = ConfigDict(hide_input_in_errors=True)

    type: Literal["cofy_api"] = "cofy_api"
    title: str = DEFAULT_ARGS["title"]
    description: str = DEFAULT_ARGS["description"]
    debug_mode: bool = False
    debug_dir: Path | None = None
    revision: int | None = None
    modules: "list[AnyModuleSettings]" = []
    auth: "AnyAuthSettings | None" = None
    resources: "list[AnyResourceSettings]" = []
    secrets: list[SecretSettings] = []

    # Resources are only built when referenced, and secrets only revealed, see convert().
    _not_converted: ClassVar[frozenset[str]] = frozenset({"type", "resources", "secrets"})

    @model_validator(mode="after")
    def _check_references(self):
        check_references(self.resources, self.secrets, self.modules, self.auth)
        return self

    def convert(self) -> Any:
        with resolving(self.resources, self.secrets):
            return super().convert()


class CofyAPI(FastAPI, FromSettingsMixin, settings=CofyAPISettings):
    def __init__(
        self,
        *,
        auth: Auth | None = None,
        debug_mode: bool = False,
        debug_dir: Path | None = None,
        revision: int | None = None,
        modules: list[Module] | None = None,
        **kwargs,
    ):
        if auth is not None:
            if "dependencies" in kwargs:
                kwargs["dependencies"].append(Depends(auth.verify))
            else:
                kwargs["dependencies"] = [Depends(auth.verify)]
        if revision is not None:
            # As semver build metadata, so the version changes with both the software and the configuration.
            kwargs["version"] = f"{kwargs.get('version', DEFAULT_ARGS['version'])}+{revision}"
        super().__init__(**(DEFAULT_ARGS | kwargs))
        self.revision = revision
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

    def openapi(self, request: Request | None = None) -> dict[str, Any]:
        """The schema, with the path *request* was served under as its first server, as it may be mounted in another."""
        self.openapi_tags = self.tags_metadata
        schema = super().openapi()
        root_path = request.scope.get("root_path", "").rstrip("/") if request else ""
        if root_path and root_path not in {server.get("url") for server in schema.get("servers", [])}:
            # A copy, as FastAPI keeps the schema to hand out again.
            schema = {**schema, "servers": [{"url": root_path}, *schema.get("servers", [])]}
        return schema

    def register_module(self, module: Module):
        self._modules.append(module)
        self.include_router(module)

    def health_check(self, request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "revision": self.revision})

    @property
    def tags_metadata(self) -> list[dict[str, Any]]:
        return [module.tag for module in self._modules]

    @property
    def modules(self) -> tuple[Module, ...]:
        return tuple(self._modules)
