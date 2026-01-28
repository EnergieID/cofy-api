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
    def tags_metadata(self) -> list[dict[str, str]]:
        tags = []
        for module_type, instances in self._modules.items():
            type_description = ""
            # Get type description from any instance of the module type
            for instance in instances.values():
                type_description = instance.type_description
                break
            tags.append(
                {
                    "name": module_type,
                    "description": type_description,
                    "x-implementations": [
                        f"{module_type}:{instance.name}"
                        for instance in instances.values()
                    ],
                }
            )
            for instance in instances.values():
                instance_description = instance.instance_description
                if instance_description:
                    tags.append(
                        {
                            "name": f"{module_type}:{instance.name}",
                            "description": instance_description,
                        }
                    )
        return tags
