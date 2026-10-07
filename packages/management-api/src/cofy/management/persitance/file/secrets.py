from cofy.api import SecretSettings

from ...errors import ResourceAlreadyExistsError, ResourceNotFoundError
from ..secrets import SecretsPersistence
from .base import FilePersistence


class FileSecretsPersistence(FilePersistence, SecretsPersistence):
    def all(self, slug: str) -> list[SecretSettings]:
        with self._open_community_config(slug, "read") as config:
            return config.secrets

    def get(self, slug: str, name: str) -> SecretSettings:
        with self._open_community_config(slug, "read") as config:
            for secret in config.secrets:
                if secret.name == name:
                    return secret
            raise ResourceNotFoundError(f"Secret {name!r} not found")

    def create(self, slug: str, secret: SecretSettings) -> SecretSettings:
        with self._open_community_config(slug, "write") as config:
            if any(existing.name == secret.name for existing in config.secrets):
                raise ResourceAlreadyExistsError(f"Secret {secret.name!r} already exists")
            config.secrets = config.secrets + [secret]
            return secret

    def replace(self, slug: str, name: str, secret: SecretSettings) -> SecretSettings:
        with self._open_community_config(slug, "write") as config:
            index = next((i for i, existing in enumerate(config.secrets) if existing.name == name), None)
            if index is None:
                raise ResourceNotFoundError(f"Secret {name!r} not found")
            config.secrets[index] = secret
            return secret

    def delete(self, slug: str, name: str) -> None:
        with self._open_community_config(slug, "write") as config:
            for i, secret in enumerate(config.secrets):
                if secret.name == name:
                    del config.secrets[i]
                    return
            raise ResourceNotFoundError(f"Secret {name!r} not found")
