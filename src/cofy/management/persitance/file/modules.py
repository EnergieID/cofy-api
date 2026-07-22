from cofy.api.module import ModuleSettings

from ...errors import ResourceNotFoundError
from ..modules import ModulesPersistence
from .base import FilePersistence


class FileModulesPersistence(FilePersistence, ModulesPersistence):
    def all(self, slug: str) -> list[ModuleSettings]:
        return self._get_community_config(slug).modules

    def get(self, slug: str, module_type: str, name: str) -> ModuleSettings:
        for module in self._get_community_config(slug).modules:
            if (module.type, module.name) == (module_type, name):
                return module
        raise ResourceNotFoundError(f"Module {module_type}:{name} not found")

    def create(self, slug: str, module: ModuleSettings) -> ModuleSettings:
        config = self._get_community_config(slug)
        if any((module.type, module.name) == (m.type, m.name) for m in config.modules):
            raise ValueError(f"Module {module.type}:{module.name} already exists")
        config.modules = config.modules + [module]
        self._save_community_config(slug, config)
        return module

    def replace(self, slug: str, module_type: str, name: str, module: ModuleSettings) -> ModuleSettings:
        config = self._get_community_config(slug)
        for i, m in enumerate(config.modules):
            if (m.type, m.name) == (module_type, name):
                config.modules[i] = module
                self._save_community_config(slug, config)
                return module
        raise ResourceNotFoundError(f"Module {module_type}:{name} not found")

    def delete(self, slug: str, module_type: str, name: str) -> None:
        config = self._get_community_config(slug)
        for i, module in enumerate(config.modules):
            if (module.type, module.name) == (module_type, name):
                del config.modules[i]
                self._save_community_config(slug, config)
                return
        raise ResourceNotFoundError(f"Module {module_type}:{name} not found")
