from abc import ABC, abstractmethod
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader, APIKeyQuery
from pydantic import BaseModel, SecretStr
from starlette.status import HTTP_401_UNAUTHORIZED

from .from_settings_mixin import BaseSettingsModel, FromSettingsMixin


class AuthSettings(BaseSettingsModel):
    type: str = "auth"


class Auth(FromSettingsMixin, ABC, settings=AuthSettings):
    @abstractmethod
    def verify(self, request: Request, *args, **kwargs):
        """Verify the request."""


class TokenInfo(BaseModel):
    name: str
    expires: datetime | None = None

    def is_expired(self) -> bool:
        if self.expires:
            if self.expires.tzinfo is None:
                self.expires = self.expires.replace(tzinfo=UTC)

            return datetime.now(UTC) > self.expires
        return False


class TokenAuthSettings(AuthSettings):
    type: str = "token"
    tokens: dict[SecretStr, TokenInfo] = {}


class TokenAuth(Auth, settings=TokenAuthSettings):
    def __init__(self, tokens: dict[str, TokenInfo]):
        self.tokens = tokens

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

        token_info = self.tokens.get(token)
        if not token_info:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token")

        if token_info.is_expired():
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Token expired")
        request.state.token = token
        request.state.auth_info = auth_info
