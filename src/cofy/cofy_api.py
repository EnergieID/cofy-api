from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from src.cofy.docs_router import DocsRouter
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
    _modules: dict[str, dict[str, Module]] = {}

    def __init__(self, **kwargs):
        super().__init__(**(DEFAULT_ARGS | kwargs))
        self.include_router(DocsRouter(self.openapi))

    def openapi(self):
        return get_openapi(
            title=self.title,
            version=self.version,
            routes=self.routes,
            tags=self.tags_metadata,
        )

    def register_module(self, module: Module):
        if module.type not in self._modules:
            self._modules[module.type] = {}
        self._modules[module.type][module.name] = module

        self.include_router(module)

    @property
    def tags_metadata(self) -> list[dict[str, Any]]:
        return [instance.tag for instances_of_type in self._modules.values() for instance in instances_of_type.values()]
