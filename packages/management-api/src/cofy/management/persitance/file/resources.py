from cofy.api import ResourceSettings

from ...errors import ResourceAlreadyExistsError, ResourceNotFoundError
from ..resources import ResourcesPersistence
from .base import FilePersistence


class FileResourcesPersistence(FilePersistence, ResourcesPersistence):
    def all(self, slug: str) -> list[ResourceSettings]:
        with self._open_community_config(slug, "read") as config:
            return config.resources

    def get(self, slug: str, name: str) -> ResourceSettings:
        with self._open_community_config(slug, "read") as config:
            for resource in config.resources:
                if resource.name == name:
                    return resource
            raise ResourceNotFoundError(f"Resource {name!r} not found")

    def create(self, slug: str, resource: ResourceSettings) -> ResourceSettings:
        with self._open_community_config(slug, "write") as config:
            if any(existing.name == resource.name for existing in config.resources):
                raise ResourceAlreadyExistsError(f"Resource {resource.name!r} already exists")
            config.resources = config.resources + [resource]
            return resource

    def replace(self, slug: str, name: str, resource: ResourceSettings) -> ResourceSettings:
        with self._open_community_config(slug, "write") as config:
            index = next((i for i, existing in enumerate(config.resources) if existing.name == name), None)
            if index is None:
                raise ResourceNotFoundError(f"Resource {name!r} not found")

            config.resources[index] = resource
            return resource

    def delete(self, slug: str, name: str) -> None:
        with self._open_community_config(slug, "write") as config:
            for i, resource in enumerate(config.resources):
                if resource.name == name:
                    del config.resources[i]
                    return
            raise ResourceNotFoundError(f"Resource {name!r} not found")
