from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from src.cofy.db.cofy_db import CofyDB
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
    _modules: dict[str, dict[str, Module]]

    def __init__(self, db: CofyDB | None = None, **kwargs):
        super().__init__(**(DEFAULT_ARGS | kwargs))
        self._modules = {}
        self._db = db
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
        if self._db:
            self._db.register_module(module)

    @property
    def tags_metadata(self) -> list[dict[str, str]]:
        tags = []
        for instances_of_type in self._modules.values():
            type_tag = next(iter(instances_of_type.values())).type_tag
            type_tag["x-implementations"] = [
                instance.tag["name"] for instance in instances_of_type.values()
            ]
            tags.append(type_tag)
            tags += [instance.tag for instance in instances_of_type.values()]
        return tags

    @property
    def db(self) -> CofyDB:
        assert self._db is not None, (
            "CofyDB instance is not configured for this CofyApi."
        )
        return self._db
