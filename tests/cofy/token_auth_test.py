from datetime import datetime as dt
from datetime import timedelta

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from starlette.status import HTTP_401_UNAUTHORIZED

from src.cofy.token_auth import token_verifier

# Example tokens for testing
tokens = {
    "infinitetoken": {"name": "testuser", "expires": None},
    "validtoken": {
        "name": "validuser",
        "expires": (dt.now() + timedelta(days=15)).isoformat(),
    },
    "expiredtoken": {"name": "expireduser", "expires": "2000-01-01T00:00:00"},
}


def test_token_verifier_error_on_invalid_token_info():
    invalid_tokens_list = [
        {"": {"expires": None}},  # Missing name
        {"nameless": {}},  # Missing name
        {"badexpire": {"name": "user", "expires": "not-a-date"}},  # Bad expires format
    ]
    for invalid_tokens in invalid_tokens_list:
        with pytest.raises(ValueError):
            token_verifier(invalid_tokens)


class TestTokenAuth:
    def protected(self):
        return {"message": "Access granted"}

    def setup_method(self):
        self.app = FastAPI(dependencies=[Depends(token_verifier(tokens))])
        self.app.add_api_route("/protected", self.protected)
        self.client = TestClient(self.app)

    def test_missing_token(self):
        response = self.client.get("/protected")
        assert response.status_code == HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Missing token"

    def test_invalid_token(self):
        response = self.client.get(
            "/protected", headers={"Authorization": "Bearer wrongtoken"}
        )
        assert response.status_code == HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Invalid token"

    def test_expired_token(self):
        response = self.client.get(
            "/protected", headers={"Authorization": "Bearer expiredtoken"}
        )
        assert response.status_code == HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Token expired"

    def test_valid_token_header(self):
        response = self.client.get(
            "/protected", headers={"Authorization": "Bearer validtoken"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Access granted"

    def test_valid_token_query(self):
        response = self.client.get("/protected?token=validtoken")
        assert response.status_code == 200
        assert response.json()["message"] == "Access granted"

    def test_invalid_token_format(self):
        response = self.client.get(
            "/protected", headers={"Authorization": "InvalidFormat validtoken"}
        )
        assert response.status_code == HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Invalid token format"

    def test_infinitetoken(self):
        response = self.client.get(
            "/protected", headers={"Authorization": "Bearer infinitetoken"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Access granted"
