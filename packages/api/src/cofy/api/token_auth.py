import hashlib
import secrets
import string
import zlib
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Literal, Self

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader, APIKeyQuery
from pydantic import BaseModel, Field, model_validator
from starlette.status import HTTP_401_UNAUTHORIZED

from .from_settings_mixin import BaseSettingsModel, FromSettingsMixin
from .secret import NAME_PATTERN, SecretValue

KEY_PREFIX = "cofy_"
HASH_PATTERN = r"^sha256:[0-9a-f]{64}$"
_BASE62 = string.digits + string.ascii_letters


def _base62(number: int, length: int) -> str:
    digits = ""
    while number:
        number, digit = divmod(number, 62)
        digits = _BASE62[digit] + digits
    return digits.rjust(length, "0")


def generate_key() -> str:
    """A new random API key: `cofy_`, 32 random base62 characters and a 6 character CRC32 checksum of those."""
    random = "".join(secrets.choice(_BASE62) for _ in range(32))
    return f"{KEY_PREFIX}{random}{_base62(zlib.crc32(random.encode()), 6)}"


def hash_key(key: str) -> str:
    """The hash an API key is stored as."""
    return f"sha256:{hashlib.sha256(key.encode()).hexdigest()}"


class AuthSettings(BaseSettingsModel):
    type: Literal["auth"] = "auth"


class Auth(FromSettingsMixin, ABC, settings=AuthSettings, abstract=True):
    @abstractmethod
    def verify(self, request: Request, *args, **kwargs):
        """Verify the request."""


class TokenInfo(BaseModel):
    """An API token, given as its key, its hash, or both - in which case the hash is the one used."""

    name: str = Field(description="The machine name of the token.", pattern=NAME_PATTERN)
    description: str | None = Field(None, description="A short description of the token, e.g. who uses it.")
    expires: datetime | None = Field(None, description="When the token stops being accepted.")
    hash: str | None = Field(None, description="The hash of the key, see `hash_key`.", pattern=HASH_PATTERN)
    key: SecretValue | None = Field(None, description="The key itself.", min_length=1)

    @model_validator(mode="after")
    def _check_key_or_hash(self) -> Self:
        if self.hash is None and self.key is None:
            raise ValueError(f"Token {self.name!r} needs a hash or a key")
        return self

    def digest(self) -> str:
        """The hash of this token's key."""
        if self.hash is not None:
            return self.hash
        assert self.key is not None
        return hash_key(self.key.get_secret_value())

    def is_expired(self) -> bool:
        if self.expires:
            if self.expires.tzinfo is None:
                self.expires = self.expires.replace(tzinfo=UTC)

            return datetime.now(UTC) > self.expires
        return False


class TokenAuthSettings(AuthSettings):
    type: Literal["token"] = "token"
    tokens: list[TokenInfo] = []

    @model_validator(mode="after")
    def _check_unique(self) -> Self:
        names = [token.name for token in self.tokens]
        if len(set(names)) != len(names):
            raise ValueError("Token names must be unique")
        digests = [token.digest() for token in self.tokens]
        if len(set(digests)) != len(digests):
            raise ValueError("Token keys must be unique")
        return self


class TokenAuth(Auth, settings=TokenAuthSettings):
    def __init__(self, tokens: list[TokenInfo]):
        self.tokens = {token.digest(): token for token in tokens}

    def verify(
        self,
        request: Request,
        header_token: str = Depends(APIKeyHeader(name="Authorization", auto_error=False, scheme_name="header")),
        query_token: str = Depends(APIKeyQuery(name="token", auto_error=False, scheme_name="query")),
    ):
        token = None
        auth_info = None
        if header_token and header_token.lower().startswith("bearer "):
            token = header_token[7:]
            auth_info = {
                "scheme": "header",
                "content": header_token,
            }
        elif query_token:
            token = query_token
            auth_info = {
                "scheme": "query",
                "content": query_token,
            }
        if not token:
            if header_token:
                raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token format")

            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Missing token")

        # Looked up by hash, which an attacker can't steer, so the lookup's timing reveals nothing of the stored keys.
        token_info = self.tokens.get(hash_key(token))
        if not token_info:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token")

        if token_info.is_expired():
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Token expired")
        request.state.token = token
        request.state.auth_info = auth_info
