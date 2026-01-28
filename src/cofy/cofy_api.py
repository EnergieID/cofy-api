from typing import Any

from fastapi import FastAPI

from src.cofy.docs_router import DocsRouter
from src.cofy.modules_router import ModulesRouter
from src.shared.module import Module

DEFAULT_ARGS: dict[str, Any] = {
    "title": "Cofy API",
    "version": "0.1.0",
    "description": "Modular cloud API for energy data",
    "docs_url": None,
    "redoc_url": None,
    "openapi_url": None,
}


class CofyApi(FastAPI):
    _modulesRouter: ModulesRouter
    _modules: dict[str, dict[str, Module]] = {}

    def __init__(self, **kwargs):
        super().__init__(**DEFAULT_ARGS, **kwargs)
        self._modulesRouter = ModulesRouter(self)
        self.include_router(self._modulesRouter, tags=["modules"])
        self.include_router(
            DocsRouter(
                title=self.title,
                version=self.version,
                routes=self.routes,
            )
        )

    def register_module(self, module: Module):
        if module.type not in self._modules:
            self._modules[module.type] = {}
        self._modules[module.type][module.name] = module
        module.cofy = self

        self.include_router(
            module,
            prefix=self._modulesRouter.module_endpoint(module),
            tags=[module.type, f"{module.type}:{module.name}"],
        )

    def get_modules(self) -> dict[str, dict[str, Module]]:
        return self._modules

    def get_module(self, module_type: str, module_name: str) -> Module | None:
        return self._modules.get(module_type, {}).get(module_name)

    def get_modules_by_type(self, module_type: str) -> dict[str, Module]:
        return self._modules.get(module_type, {})
