from __future__ import annotations
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from src.cofy.app import Cofy

from fastapi import APIRouter

class ModuleResponse(BaseModel):
    module_type: str
    module_name: str
    endpoint: str
    metadata: dict

class ModuleTypeResponse(BaseModel):
    module_type: str
    modules: list[ModuleResponse]

class CofyApi:
    cofy: Cofy
    router: APIRouter

    def __init__(self, cofy: Cofy):
        self.cofy = cofy
        self.router = APIRouter()
        self.router.add_api_route("/", self.get_modules, methods=["GET"])
        self.router.add_api_route(
            "/{module_type}", self.get_modules_by_type, methods=["GET"]
        )
        self.router.add_api_route(
            "/{module_type}/{module_name}", self.get_module, methods=["GET"]
        )

    def get_modules(self) -> list[ModuleTypeResponse]:
        return [
            ModuleTypeResponse(
                module_type=module_type,
                modules=self.get_modules_by_type(module_type),
            )
            for module_type in self.cofy.modules.keys()
        ]

    def get_modules_by_type(self, module_type: str) -> list[ModuleResponse]:
        return [
                    self.get_module(module_type, module_name)
                    for module_name in self.cofy.get_modules_by_type(module_type).keys()
                ]

    def get_module(self, module_type: str, module_name: str) -> ModuleResponse:
        return ModuleResponse(
                        module_type=module_type,
                        module_name=module_name,
                        endpoint=f"/{module_type}/{module_name}",
                        metadata=self.cofy.get_module(module_type, module_name).settings,
                    )
    
    
