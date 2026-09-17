"""Integration tests for AllowedModulesRouter.

The catalog is what a schema-driven frontend builds every module form from, so these tests
pin the properties it relies on: only constructible types, self-contained schemas, an intact
discriminator, and credentials marked as secrets.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cofy.management.api.allowed_modules import AllowedModulesRouter
from cofy.management.errors import add_exception_handlers


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    add_exception_handlers(app)
    app.include_router(AllowedModulesRouter().router)
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def catalog(client: TestClient) -> list[dict]:
    r = client.get("/management/communities/test/allowed-modules")
    assert r.status_code == 200
    return r.json()


def _by_type(catalog: list[dict], type_name: str) -> dict:
    return next(entry for entry in catalog if entry["type"] == type_name)


# ── catalog contents ──────────────────────────────────────────────────────


def test_lists_the_installed_module_types(catalog: list[dict]):
    types = {entry["type"] for entry in catalog}
    assert {"billing", "tariff", "timeseries", "members", "production", "directive"} <= types


def test_excludes_abstract_module_types(catalog: list[dict]):
    """`ModuleSettings` is registered under "module" but `Module` cannot be instantiated."""
    assert "module" not in {entry["type"] for entry in catalog}


def test_entries_are_sorted_by_type(catalog: list[dict]):
    types = [entry["type"] for entry in catalog]
    assert types == sorted(types)


def test_each_entry_exposes_type_description_and_schema(catalog: list[dict]):
    for entry in catalog:
        assert sorted(entry) == ["description", "schema", "type"]
        assert entry["description"]
        assert entry["schema"]["type"] == "object"


def test_description_comes_from_the_module_class(catalog: list[dict]):
    assert _by_type(catalog, "tariff")["description"] == "Module providing tariff data as time series."


# ── schema shape the frontend depends on ──────────────────────────────────


def test_schema_is_self_contained(catalog: list[dict]):
    """Nested models resolve to local `$defs`, so no companion document is needed."""
    schema = _by_type(catalog, "tariff")["schema"]

    assert "$defs" in schema
    refs = _all_refs(schema)
    assert refs, "expected the tariff schema to reference nested models"
    assert all(ref.startswith("#/$defs/") for ref in refs), refs


def test_schema_has_no_input_output_split(catalog: list[dict]):
    """FastAPI's inferred schemas pair `-Input`/`-Output`; the validation schema does not."""
    for entry in catalog:
        names = list(entry["schema"].get("$defs", {}))
        assert not [n for n in names if n.endswith(("-Input", "-Output"))], names


def test_polymorphic_field_keeps_its_discriminator(catalog: list[dict]):
    """Without this a client cannot tell which `oneOf` branch a `type` selects."""
    source = _by_type(catalog, "tariff")["schema"]["properties"]["source"]

    assert source["discriminator"]["propertyName"] == "type"
    mapping = source["discriminator"]["mapping"]
    assert mapping["entsoe_day_ahead"] == "#/$defs/EntsoeDayAheadTariffSourceSettings"
    # every branch is reachable through the mapping, and the mapping points nowhere else
    assert set(mapping.values()) == {branch["$ref"] for branch in source["oneOf"]}


def test_type_property_pins_the_discriminator_value(catalog: list[dict]):
    schema = _by_type(catalog, "tariff")["schema"]
    assert schema["properties"]["type"]["const"] == "tariff"


def test_credentials_are_marked_write_only_passwords(catalog: list[dict]):
    """So a generated form renders a password input without needing a UI hint."""
    defs = _by_type(catalog, "tariff")["schema"]["$defs"]
    api_key = defs["EntsoeDayAheadTariffSourceSettings"]["properties"]["api_key"]

    assert api_key["format"] == "password"
    assert api_key["writeOnly"] is True


def _all_refs(node: object) -> list[str]:
    """Every `$ref` value anywhere in a schema."""
    if isinstance(node, dict):
        found = [node["$ref"]] if isinstance(node.get("$ref"), str) else []
        for value in node.values():
            found += _all_refs(value)
        return found
    if isinstance(node, list):
        return [ref for item in node for ref in _all_refs(item)]
    return []
