from __future__ import annotations
from fastapi import APIRouter

class CofyApi:
    cofy: src.cofy.app.Cofy
    router: APIRouter

    def __init__(self, cofy: src.cofy.app.Cofy):
        self.cofy = cofy
        self.router = APIRouter()
        self.router.add_api_route("/", self.get_modules, methods=["GET"])
        self.router.add_api_route("/{module_type}", self.get_modules_by_type, methods=["GET"])
        self.router.add_api_route("/{module_type}/{module_name}", self.get_module, methods=["GET"])

    def get_modules(self):
        return self.cofy.modules
    
    def get_modules_by_type(self, module_type: str):
        return self.cofy.get_modules_by_type(module_type)
    
    def get_module(self, module_type: str, module_name: str):
        return self.cofy.get_module(module_type, module_name)

