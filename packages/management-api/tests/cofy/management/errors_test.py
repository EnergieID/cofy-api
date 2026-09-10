"""Tests for the RFC 9457 problem+json error contract."""

from __future__ import annotations

from typing import Annotated

import pytest
from fastapi import Body, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from cofy.management.errors import (
    CONTENT_TYPE,
    ManagementError,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    add_exception_handlers,
)


class Payload(BaseModel):
    name: str
    count: int


@pytest.fixture()
def client() -> TestClient:
    """An app whose routes raise each error kind on demand."""
    app = FastAPI()
    add_exception_handlers(app)

    @app.get("/not-found")
    def not_found() -> None:
        raise ResourceNotFoundError("Module tariff:spot not found")

    @app.get("/conflict")
    def conflict() -> None:
        raise ResourceAlreadyExistsError("Module tariff:spot already exists")

    @app.get("/invariant")
    def invariant() -> None:
        raise ValueError("Community config must be a YAML mapping")

    @app.get("/unmapped")
    def unmapped() -> None:
        raise ManagementError("something went wrong")

    @app.post("/body")
    def body(payload: Annotated[Payload, Body()]) -> Payload:
        return payload

    @app.get("/param")
    def param(count: int) -> int:
        return count

    return TestClient(app, raise_server_exceptions=False)


# ── mapped domain errors ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("route", "status"),
    [
        ("/not-found", 404),
        ("/conflict", 409),
        ("/unmapped", 500),
    ],
)
def test_domain_errors_map_to_problem_documents(client: TestClient, route: str, status: int):
    r = client.get(route)

    assert r.status_code == status
    assert r.headers["content-type"] == CONTENT_TYPE
    assert r.json()["status"] == status
    assert r.json()["title"]
    assert r.json()["detail"]


def test_problem_document_omits_errors_when_there_are_none(client: TestClient):
    assert "errors" not in client.get("/not-found").json()


def test_value_error_maps_to_422(client: TestClient):
    r = client.get("/invariant")

    assert r.status_code == 422
    assert r.headers["content-type"] == CONTENT_TYPE
    assert r.json()["detail"] == "Community config must be a YAML mapping"
    assert "errors" not in r.json()  # not attributable to one field


# ── request validation ────────────────────────────────────────────────────


def test_body_validation_errors_report_pydantic_locs(client: TestClient):
    r = client.post("/body", json={"count": "not-a-number"})

    assert r.status_code == 422
    assert r.headers["content-type"] == CONTENT_TYPE
    locs = {tuple(e["loc"]) for e in r.json()["errors"]}
    assert locs == {("body", "name"), ("body", "count")}
    assert all(e["msg"] and e["type"] for e in r.json()["errors"])


def test_validation_errors_never_echo_the_submitted_value(client: TestClient):
    """pydantic includes the offending `input` in its errors; for a credential field that
    would put the secret straight back into the response body."""
    r = client.post("/body", json={"name": "x", "count": "s3cret"})

    assert "s3cret" not in r.text
    assert all("input" not in e for e in r.json()["errors"])


def test_nested_body_errors_point_at_the_nested_field(client: TestClient):
    r = client.post("/body", json={"name": "x", "count": {"nested": 1}})

    assert [tuple(e["loc"]) for e in r.json()["errors"]] == [("body", "count")]


def test_non_body_validation_errors_keep_their_own_location(client: TestClient):
    r = client.get("/param", params={"count": "not-a-number"})

    assert r.status_code == 422
    (error,) = r.json()["errors"]
    assert tuple(error["loc"]) == ("query", "count")
