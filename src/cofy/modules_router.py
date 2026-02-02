from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from src.cofy.cofy_api import CofyApi
    from src.shared.module import Module

from fastapi import APIRouter, HTTPException


class ModuleResponse(BaseModel):
    module_type: str
    module_name: str
    endpoint: str
    metadata: dict

    def __init__(self, module: Module, endpoint: str):
        super().__init__(
            module_type=module.type,
            module_name=module.name,
            endpoint=endpoint,
            metadata=module.metadata,
        )


class ModuleTypeResponse(BaseModel):
    module_type: str
    modules: list[ModuleResponse]


class ModulesRouter(APIRouter):
    cofy: CofyApi

    def __init__(self, cofy: CofyApi):
        super().__init__(prefix="/v0")
        self.cofy = cofy
        self.add_api_route("/", self.get_modules, methods=["GET"])
        self.add_api_route(
            "/{module_type}",
            self.get_modules_by_type,
            methods=["GET"],
        )
        self.add_api_route(
            "/{module_type}/{module_name}",
            self.get_module,
            methods=["GET"],
        )

    def module_endpoint(self, module: Module) -> str:
        """Returns the API endpoint for the given module."""
        return f"/v0/{module.type}/{module.name}"

    def get_modules(self) -> list[ModuleTypeResponse]:
        """Returns a list of all registered modules grouped by their type."""
        return [
            ModuleTypeResponse(
                module_type=module_type,
                modules=self.get_modules_by_type(module_type),
            )
            for module_type in self.cofy.get_modules()
        ]

    def get_modules_by_type(self, module_type: str) -> list[ModuleResponse]:
        """Returns a list of all registered modules of the given type."""
        return [
            self.get_module(module_type, module_name)
            for module_name in self.cofy.get_modules_by_type(module_type)
        ]

    def get_module(self, module_type: str, module_name: str) -> ModuleResponse:
        """Returns the module with the given type and name."""
        module = self.cofy.get_module(module_type, module_name)

        if not module:
            raise HTTPException(
                status_code=404,
                detail=f"Module {module_type}/{module_name} not found",
            )

        return ModuleResponse(module=module, endpoint=self.module_endpoint(module))
