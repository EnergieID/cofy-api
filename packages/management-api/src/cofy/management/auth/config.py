from __future__ import annotations

import datetime as dt

from cofy.modules.timeseries.model import ISOTimedelta
from pydantic import BaseModel, Field, SecretStr


class OidcConfig(BaseModel):
    """How the management API logs people in: the OpenID Connect provider it trusts, and the session it keeps."""

    issuer: str = Field(description="The identity provider's issuer URL, where its discovery document lives.")
    client_id: str = Field(description="This application's client id at the identity provider.")
    client_secret: SecretStr = Field(description="This application's client secret at the identity provider.")
    scopes: str = Field("openid profile email", description="The scopes asked for at login.")
    session_secret: SecretStr = Field(description="The key session cookies are signed with.")
    session_lifetime: ISOTimedelta = Field(dt.timedelta(hours=8), description="How long a login lasts.")
    secure_cookies: bool = Field(True, description="Whether the session cookie is only sent over HTTPS.")

    @property
    def server_metadata_url(self) -> str:
        return f"{self.issuer.rstrip('/')}/.well-known/openid-configuration"
