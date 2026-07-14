from datetime import datetime as dt
from datetime import timedelta, timezone

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from starlette.status import HTTP_401_UNAUTHORIZED

from cofy.api import TokenAuth, TokenInfo

# Example tokens for testing
tokens = {
    "infinitetoken": TokenInfo(name="testuser", expires=None),
    "validtoken": TokenInfo(
        name="validuser",
        expires=(dt.now() + timedelta(days=15)),
    ),
    "expiredtoken": TokenInfo(
        name="expireduser",
        expires=dt.fromisoformat("2000-01-01T00:00:00"),
    ),
}


class TestTokenAuth:
    def protected(self):
        return {"message": "Access granted"}

    def setup_method(self):
        self.app = FastAPI(dependencies=[Depends(TokenAuth(tokens).verify)])
        self.app.add_api_route("/protected", self.protected)
        self.client = TestClient(self.app)

    def test_missing_token(self):
        response = self.client.get("/protected")
        assert response.status_code == HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Missing token"

    def test_invalid_token(self):
        response = self.client.get("/protected", headers={"Authorization": "Bearer wrongtoken"})
        assert response.status_code == HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Invalid token"

    def test_expired_token(self):
        response = self.client.get("/protected", headers={"Authorization": "Bearer expiredtoken"})
        assert response.status_code == HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Token expired"

    def test_valid_token_header(self):
        response = self.client.get("/protected", headers={"Authorization": "Bearer validtoken"})
        assert response.status_code == 200
        assert response.json()["message"] == "Access granted"

    def test_valid_token_query(self):
        response = self.client.get("/protected?token=validtoken")
        assert response.status_code == 200
        assert response.json()["message"] == "Access granted"

    def test_invalid_token_format(self):
        response = self.client.get("/protected", headers={"Authorization": "InvalidFormat validtoken"})
        assert response.status_code == HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Invalid token format"

    def test_infinitetoken(self):
        response = self.client.get("/protected", headers={"Authorization": "Bearer infinitetoken"})
        assert response.status_code == 200
        assert response.json()["message"] == "Access granted"


def test_token_expiry_is_timezone_aware():
    token = TokenInfo(
        name="timezonetoken",
        # now + 1 minute in UTC-1, should not be expired
        expires=(dt.now(timezone(timedelta(hours=-1))) + timedelta(minutes=1)),
    )

    assert not token.is_expired()

    token = TokenInfo(
        name="timezonetoken",
        # now - 1 minute in UTC+1, should be expired
        expires=(dt.now(timezone(timedelta(hours=1))) - timedelta(minutes=1)),
    )

    assert token.is_expired()
