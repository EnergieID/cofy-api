from src.shared.module import Module

CONF_MODULE_SETTINGS_KEY = "modules"

class Cofy:
    modules: dict[str, dict[str, Module]] = {}
    settings: dict = {}

    def __init__(self, settings: dict):
        self.settings = settings

    def register_module(self, module_type: str, module_name: str, module_instance: Module):
        if module_type not in self.modules:
            self.modules[module_type] = {}
        self.modules[module_type][module_name] = module_instance
        module_instance.cofy = self

        if CONF_MODULE_SETTINGS_KEY in self.settings and \
           module_type in self.settings[CONF_MODULE_SETTINGS_KEY] and \
           module_name in self.settings[CONF_MODULE_SETTINGS_KEY][module_type]:
                module_instance.update_settings(self.settings[CONF_MODULE_SETTINGS_KEY][module_type][module_name])
    
    def get_module(self, module_type: str, module_name: str) -> Module | None:
        return self.modules.get(module_type, {}).get(module_name)
    
    def get_modules_by_type(self, module_type: str) -> dict[str, Module]:
        return self.modules.get(module_type, {})
