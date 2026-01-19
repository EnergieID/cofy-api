from fastapi import FastAPI
from src.shared.module import Module
from src.cofy.api import CofyApi

CONF_MODULE_SETTINGS_KEY = "modules"


class Cofy:
    modules: dict[str, dict[str, Module]] = {}
    settings: dict = {}
    api: FastAPI

    def __init__(self, settings: dict):
        self.settings = settings
        self.api = FastAPI()
        self.api.include_router(CofyApi(self).router)

    def register_module(self, module_type: str, module_name: str, module: Module):
        if module_type not in self.modules:
            self.modules[module_type] = {}
        self.modules[module_type][module_name] = module
        module.cofy = self

    def get_module(self, module_type: str, module_name: str) -> Module | None:
        return self.modules.get(module_type, {}).get(module_name)

    def get_modules_by_type(self, module_type: str) -> dict[str, Module]:
        return self.modules.get(module_type, {})
