from cofy.api.module import ModuleSettings
from cofy.api.secret import restore_masked_secrets

from ...errors import ResourceAlreadyExistsError, ResourceNotFoundError
from ..modules import ModulesPersistence
from .base import FilePersistence


class FileModulesPersistence(FilePersistence, ModulesPersistence):
    def all(self, slug: str) -> list[ModuleSettings]:
        with self._open_community_config(slug, "read") as config:
            return config.modules

    def get(self, slug: str, module_type: str, name: str) -> ModuleSettings:
        with self._open_community_config(slug, "read") as config:
            for module in config.modules:
                if (module.type, module.name) == (module_type, name):
                    return module
            raise ResourceNotFoundError(f"Module {module_type}:{name} not found")

    def create(self, slug: str, module: ModuleSettings) -> ModuleSettings:
        with self._open_community_config(slug, "write") as config:
            if any((module.type, module.name) == (m.type, m.name) for m in config.modules):
                raise ResourceAlreadyExistsError(f"Module {module.type}:{module.name} already exists")
            config.modules = config.modules + [module]
            return module

    def replace(self, slug: str, module_type: str, name: str, module: ModuleSettings) -> ModuleSettings:
        with self._open_community_config(slug, "write") as config:
            target_index = next(
                (i for i, m in enumerate(config.modules) if (m.type, m.name) == (module_type, name)),
                None,
            )
            if target_index is None:
                raise ResourceNotFoundError(f"Module {module_type}:{name} not found")

            collides_with_other = any(
                i != target_index and (m.type, m.name) == (module.type, module.name)
                for i, m in enumerate(config.modules)
            )
            if collides_with_other:
                raise ResourceAlreadyExistsError(f"Module {module.type}:{module.name} already exists")

            # The client built this payload from a masked read, so any secret it did not
            # deliberately change still carries the placeholder. Substitute the stored values
            # while the module being replaced is still in hand and the lock is held.
            restore_masked_secrets(module, config.modules[target_index])

            config.modules[target_index] = module
            return module

    def delete(self, slug: str, module_type: str, name: str) -> None:
        with self._open_community_config(slug, "write") as config:
            for i, module in enumerate(config.modules):
                if (module.type, module.name) == (module_type, name):
                    del config.modules[i]
                    return
            raise ResourceNotFoundError(f"Module {module_type}:{name} not found")
