from __future__ import annotations
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from src.cofy.app import Cofy
    from src.shared.module import Module

from fastapi import APIRouter

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

class CofyApi:
    cofy: Cofy
    router: APIRouter

    def __init__(self, cofy: Cofy):
        self.cofy = cofy
        self.router = APIRouter(prefix="/v1")
        self.router.add_api_route("/", self.get_modules, methods=["GET"])
        self.router.add_api_route(
            "/{module_type}", self.get_modules_by_type, methods=["GET"]
        )
        self.router.add_api_route(
            "/{module_type}/{module_name}", self.get_module, methods=["GET"]
        )

    def module_endpoint(self, module: Module) -> str:
        """Returns the API endpoint for the given module."""
        return f"/v1/{module.type}/{module.name}"

    def get_modules(self) -> list[ModuleTypeResponse]:
        """Returns a list of all registered modules grouped by their type."""
        return [
            ModuleTypeResponse(
                module_type=module_type,
                modules=self.get_modules_by_type(module_type),
            )
            for module_type in self.cofy.modules.keys()
        ]

    def get_modules_by_type(self, module_type: str) -> list[ModuleResponse]:
        """returns a list of all registered modules of the given type."""
        return [
                    self.get_module(module_type, module_name)
                    for module_name in self.cofy.get_modules_by_type(module_type).keys()
                ]

    def get_module(self, module_type: str, module_name: str) -> ModuleResponse:
        """Returns the module with the given type and name."""
        module = self.cofy.get_module(module_type, module_name)
        return ModuleResponse(module=module, endpoint=self.module_endpoint(module))
    
    
