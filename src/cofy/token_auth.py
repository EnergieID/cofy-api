from fastapi import HTTPException, Depends
from pydantic import BaseModel
from starlette.status import HTTP_401_UNAUTHORIZED
from datetime import datetime
from typing import Optional
from fastapi.security import APIKeyHeader, APIKeyQuery

class TokenInfo(BaseModel):
    name: str
    expires: Optional[str] = None

    def __init__(self, info: dict):
        if "name" not in info:
            raise ValueError("Token info must include a name")
        if "expires" in info:
            try:
                datetime.fromisoformat(info["expires"])
            except Exception:
                raise ValueError("Token expires must be in ISO8601 format")
        super().__init__(**info)
    
    def is_expired(self) -> bool:
        if self.expires:
            expires_dt = datetime.fromisoformat(self.expires)
            return datetime.now() > expires_dt
        return False
    
def token_verifier(tokens: dict) -> Optional[TokenInfo]:
    tokens = {token: TokenInfo(info) for token, info in tokens.items()}

    def verify(header_token: str = Depends(APIKeyHeader(name="Authorization", auto_error=False)),
                query_token: str = Depends(APIKeyQuery(name="token", auto_error=False))):
        token = None
        if header_token and header_token.lower().startswith("bearer "):
            token = header_token[7:]
        elif query_token:
            token = query_token
        if not token:
            if header_token:
                raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token format")

            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Missing token")
        
        token_info = tokens.get(token)
        if not token_info:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token")

        if token_info.is_expired():
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Token expired")
    return verify
