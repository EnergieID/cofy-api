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
    def __init__(self, **kwargs):
        super().__init__(**(DEFAULT_ARGS | kwargs))
        self._modules: list[Module] = []
        self.include_router(DocsRouter(self.openapi))

    def openapi(self):
        return get_openapi(
            title=self.title,
            version=self.version,
            routes=self.routes,
            tags=self.tags_metadata,
        )

    def register_module(self, module: Module):
        self._modules.append(module)
        self.include_router(module)

    @property
    def tags_metadata(self) -> list[dict[str, Any]]:
        return [module.tag for module in self._modules]

    @property
    def modules(self) -> tuple[Module, ...]:
        return tuple(self._modules)
