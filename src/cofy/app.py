from fastapi import FastAPI
from src.shared.module import Module
from src.cofy.api import CofyApi


class Cofy:
    modules: dict[str, dict[str, Module]] = {}
    settings: dict = {}
    fastApi: FastAPI
    cofyApi: CofyApi

    def __init__(self, settings: dict):
        self.settings = settings
        self.fastApi = FastAPI()
        self.cofyApi = CofyApi(self)
        self.fastApi.include_router(self.cofyApi.router)

    def register_module(self, module: Module):
        if module.type not in self.modules:
            self.modules[module.type] = {}
        self.modules[module.type][module.name] = module
        module.cofy = self

        if module.router:
            self.fastApi.include_router(
                module.router, prefix=self.cofyApi.module_endpoint(module)
            )

    def get_module(self, module_type: str, module_name: str) -> Module | None:
        return self.modules.get(module_type, {}).get(module_name)

    def get_modules_by_type(self, module_type: str) -> dict[str, Module]:
        return self.modules.get(module_type, {})
