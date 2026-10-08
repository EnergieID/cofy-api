from cofy.api import TokenAuthSettings, TokenInfo
from cofy.api.cofy_api import CofyAPISettings

from ...errors import ResourceAlreadyExistsError, ResourceNotFoundError
from ..tokens import TokensPersistence
from .base import CommunityFileStore


def _token_auth(config: CofyAPISettings) -> TokenAuthSettings:
    """The community's token auth, set up without tokens if it has no auth yet."""
    if config.auth is None:
        config.auth = TokenAuthSettings()
    if not isinstance(config.auth, TokenAuthSettings):
        raise ValueError(f"Tokens can't be managed for auth of type {config.auth.type!r}")
    return config.auth


class FileTokensPersistence(CommunityFileStore, TokensPersistence):
    def all(self, slug: str) -> list[TokenInfo]:
        with self._open_community_config(slug, "read") as config:
            return _token_auth(config).tokens

    def get(self, slug: str, name: str) -> TokenInfo:
        for token in self.all(slug):
            if token.name == name:
                return token
        raise ResourceNotFoundError(f"Token {name!r} not found")

    def create(self, slug: str, token: TokenInfo) -> TokenInfo:
        with self._open_community_config(slug, "write") as config:
            auth = _token_auth(config)
            if any(existing.name == token.name for existing in auth.tokens):
                raise ResourceAlreadyExistsError(f"Token {token.name!r} already exists")
            auth.tokens = auth.tokens + [token]
            return token

    def replace(self, slug: str, name: str, token: TokenInfo) -> TokenInfo:
        with self._open_community_config(slug, "write") as config:
            tokens = _token_auth(config).tokens
            index = next((i for i, existing in enumerate(tokens) if existing.name == name), None)
            if index is None:
                raise ResourceNotFoundError(f"Token {name!r} not found")
            tokens[index] = token
            return token

    def delete(self, slug: str, name: str) -> None:
        with self._open_community_config(slug, "write") as config:
            tokens = _token_auth(config).tokens
            for i, token in enumerate(tokens):
                if token.name == name:
                    del tokens[i]
                    return
            raise ResourceNotFoundError(f"Token {name!r} not found")
