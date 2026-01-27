from datetime import datetime

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader, APIKeyQuery
from pydantic import BaseModel
from starlette.status import HTTP_401_UNAUTHORIZED


class TokenInfo(BaseModel):
    name: str
    expires: str | None = None

    def __init__(self, info: dict):
        if "name" not in info or not info["name"]:
            raise ValueError("Token info must include a name")
        if "expires" in info and info["expires"] is not None:
            try:
                datetime.fromisoformat(info["expires"])
            except Exception:
                raise ValueError("Token expires must be in ISO8601 format") from None
        super().__init__(**info)

    def is_expired(self) -> bool:
        if self.expires:
            expires_dt = datetime.fromisoformat(self.expires)
            return datetime.now() > expires_dt
        return False


def token_verifier(tokens: dict):
    tokens = {token: TokenInfo(info) for token, info in tokens.items()}

    def verify(
        request: Request,
        header_token: str = Depends(
            APIKeyHeader(name="Authorization", auto_error=False, scheme_name="header")
        ),
        query_token: str = Depends(
            APIKeyQuery(name="token", auto_error=False, scheme_name="query")
        ),
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
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token format"
                )

            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED, detail="Missing token"
            )

        token_info = tokens.get(token)
        if not token_info:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )

        if token_info.is_expired():
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED, detail="Token expired"
            )
        request.state.token = token
        request.state.auth_info = auth_info

    return verify
