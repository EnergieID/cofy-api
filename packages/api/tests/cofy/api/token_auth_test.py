import re
import zlib
from datetime import datetime as dt
from datetime import timedelta, timezone

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from starlette.status import HTTP_401_UNAUTHORIZED

from cofy.api import TokenAuth, TokenAuthSettings, TokenInfo, generate_key, hash_key
from cofy.api.token_auth import _base62

# Example tokens for testing
tokens = [
    TokenInfo(name="infinite", key="infinitetoken"),
    TokenInfo(name="valid", key="validtoken", expires=(dt.now() + timedelta(days=15))),
    TokenInfo(name="expired", key="expiredtoken", expires=dt.fromisoformat("2000-01-01T00:00:00")),
    TokenInfo(name="hashed", hash=hash_key("hashedtoken")),
    TokenInfo(name="both", key="ignoredtoken", hash=hash_key("preferredtoken")),
]


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

    def test_hashed_token(self):
        response = self.client.get("/protected", headers={"Authorization": "Bearer hashedtoken"})
        assert response.status_code == 200

    def test_a_hash_is_not_a_key(self):
        response = self.client.get("/protected", headers={"Authorization": f"Bearer {hash_key('hashedtoken')}"})
        assert response.status_code == HTTP_401_UNAUTHORIZED

    def test_hash_is_preferred_over_key(self):
        assert self.client.get("/protected?token=preferredtoken").status_code == 200
        assert self.client.get("/protected?token=ignoredtoken").status_code == HTTP_401_UNAUTHORIZED


def test_token_expiry_is_timezone_aware():
    token = TokenInfo(
        name="timezonetoken",
        key="key",
        # now + 1 minute in UTC-1, should not be expired
        expires=(dt.now(timezone(timedelta(hours=-1))) + timedelta(minutes=1)),
    )

    assert not token.is_expired()

    token = TokenInfo(
        name="timezonetoken",
        key="key",
        # now - 1 minute in UTC+1, should be expired
        expires=(dt.now(timezone(timedelta(hours=1))) - timedelta(minutes=1)),
    )

    assert token.is_expired()


def test_token_needs_a_key_or_a_hash():
    with pytest.raises(ValidationError, match="needs a hash or a key"):
        TokenInfo(name="nothing")


@pytest.mark.parametrize("fields", [{"key": ""}, {"hash": "md5:abc"}, {"hash": "sha256:" + "A" * 64}])
def test_token_rejects_an_invalid_key_or_hash(fields):
    with pytest.raises(ValidationError):
        TokenInfo(name="invalid", **fields)


def test_token_name_is_a_machine_name():
    with pytest.raises(ValidationError):
        TokenInfo(name="Demo User", key="key")


def test_token_key_is_only_revealed_on_disk():
    token = TokenInfo(name="demo", key="secretkey")

    assert "secretkey" not in str(token.model_dump())
    assert token.model_dump(round_trip=True)["key"] == "secretkey"


def test_token_names_are_unique():
    with pytest.raises(ValidationError, match="names must be unique"):
        TokenAuthSettings(tokens=[TokenInfo(name="demo", key="a"), TokenInfo(name="demo", key="b")])


def test_token_keys_are_unique():
    with pytest.raises(ValidationError, match="keys must be unique"):
        TokenAuthSettings(tokens=[TokenInfo(name="a", key="same"), TokenInfo(name="b", hash=hash_key("same"))])


def test_settings_build_token_auth():
    auth = TokenAuthSettings.model_validate({"tokens": [{"name": "demo", "key": "demokey"}]}).convert()

    assert isinstance(auth, TokenAuth)
    assert auth.tokens[hash_key("demokey")].name == "demo"


def test_generated_key_format():
    key = generate_key()

    assert re.fullmatch(r"cofy_[0-9A-Za-z]{38}", key)
    random, checksum = key[5:37], key[37:]
    assert checksum == _base62(zlib.crc32(random.encode()), 6)


def test_generated_keys_differ():
    assert generate_key() != generate_key()


def test_hash_key():
    assert hash_key("demo") == "sha256:2a97516c354b68848cdbd8f54a226a0a55b21ed138e207ad6c5cbb9c00aa5aea"
