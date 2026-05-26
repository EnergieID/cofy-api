import builtins
import datetime as dt

import energy_cost as ec
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cofy.modules.members import (
    Address,
    ConnectionType,
    Contract,
    CustomerType,
    Member,
    MembersModule,
    MemberSource,
    NamedIdentifier,
)

# Register a lightweight supplier so _build_contract_history can resolve supplier_key + product_key.
# This is done at import time so it is available for all tests in this module.
_SUPPLIER_KEY = "test_supplier"
_PRODUCT_KEY = "test_product"
if _SUPPLIER_KEY not in dict(ec.Supplier.items()):
    from energy_cost import Tariff

    ec.Supplier.register(_SUPPLIER_KEY, ec.Supplier(products={_PRODUCT_KEY: Tariff(root=[])}))


def _make_contract(ean: str, start: dt.datetime, end: dt.datetime | None = None) -> Contract:
    return Contract(
        ean=ean,
        customer_type=CustomerType.RESIDENTIAL,
        connection_type=ConnectionType.ELECTRICITY,
        supplier=NamedIdentifier(name="Test Supplier", id=_SUPPLIER_KEY),
        product=NamedIdentifier(name="Test Product", id=_PRODUCT_KEY),
        distributor=NamedIdentifier(name="Fluvius Imewo", id="fluvius_imewo"),
        region=NamedIdentifier(name="Flanders", id="be_flanders"),
        start_date=start,
        end_date=end,
        last_invoice_date=None,
        is_green=False,
    )


class DummyMemberSource(MemberSource[Member]):
    response_model = Member

    def __init__(self):
        self.activation_codes = {
            "code-a": "1",
            "code-b": "2",
        }
        contracts = [
            _make_contract(
                "EAN123",
                start=dt.datetime(2024, 1, 1, tzinfo=dt.UTC),
                end=dt.datetime(2025, 6, 1, tzinfo=dt.UTC),
            ),
            _make_contract(
                "EAN123",
                start=dt.datetime(2025, 6, 1, tzinfo=dt.UTC),
            ),
        ]
        self.members = [
            Member(id="1", addresses=[Address(contracts=contracts)]),
            Member(id="2"),
        ]

    def list(self, email: str | None = None) -> builtins.list[Member]:
        return self.members

    def get(self, member_id: str) -> Member | None:
        return next((m for m in self.members if m.id == member_id), None)

    def verify(self, activation_code: str) -> Member | None:
        member_id = self.activation_codes.get(activation_code)
        if member_id is None:
            return None
        return next((member for member in self.members if member.id == member_id), None)


def test_members_module_list_and_verify_routes():
    app = FastAPI()
    module = MembersModule(source=DummyMemberSource(), name="dummy")
    app.include_router(module)
    client = TestClient(app)

    response = client.get(module.prefix)
    assert response.status_code == 200
    assert len(response.json()) == 2

    response = client.post(module.prefix + "/verify", json={"activation_code": "code-a"})
    assert response.status_code == 200
    assert response.json()["id"] == "1"

    response = client.post(module.prefix + "/verify", json={"activation_code": "invalid"})
    assert response.status_code == 404


def test_members_module_get_by_id():
    app = FastAPI()
    module = MembersModule(source=DummyMemberSource(), name="dummy")
    app.include_router(module)
    client = TestClient(app)

    response = client.get(module.prefix + "/1")
    assert response.status_code == 200
    assert response.json()["id"] == "1"

    response = client.get(module.prefix + "/nonexistent")
    assert response.status_code == 404


def test_removed_activation_get_endpoints_return_404():
    app = FastAPI()
    module = MembersModule(source=DummyMemberSource(), name="dummy")
    app.include_router(module)
    client = TestClient(app)

    response = client.get(module.prefix + "/activation/code-a")
    assert response.status_code == 404

    response = client.get(module.prefix + "/activation/code-a/validate")
    assert response.status_code == 404


class TestGetContractHistory:
    def setup_method(self):
        app = FastAPI()
        module = MembersModule(source=DummyMemberSource(), name="dummy")
        app.include_router(module)
        self.client = TestClient(app)
        self.prefix = module.prefix

    def test_returns_200_for_known_ean(self):
        response = self.client.get(self.prefix + "/1/contracts/EAN123")
        assert response.status_code == 200

    def test_response_contains_versions(self):
        response = self.client.get(self.prefix + "/1/contracts/EAN123")
        body = response.json()
        assert "versions" in body
        assert len(body["versions"]) == 2

    def test_versions_have_start_date(self):
        response = self.client.get(self.prefix + "/1/contracts/EAN123")
        versions = response.json()["versions"]
        assert versions[0]["start"] is not None
        assert versions[1]["start"] is not None

    def test_returns_404_for_unknown_ean(self):
        response = self.client.get(self.prefix + "/1/contracts/UNKNOWN_EAN")
        assert response.status_code == 404

    def test_returns_404_for_member_without_contracts(self):
        response = self.client.get(self.prefix + "/2/contracts/EAN123")
        assert response.status_code == 404

    def test_returns_404_for_unknown_member(self):
        response = self.client.get(self.prefix + "/nonexistent/contracts/EAN123")
        assert response.status_code == 404
