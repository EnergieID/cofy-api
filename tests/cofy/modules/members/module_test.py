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
from cofy.modules.members.source import MemberSourceSettings

# Register a lightweight supplier so _build_contract_history can resolve supplier_key + product_key.
# This is done at import time so it is available for all tests in this module.
_SUPPLIER_KEY = "test_supplier"
_PRODUCT_KEY = "test_product"
if _SUPPLIER_KEY not in dict(ec.Supplier.items()):
    from energy_cost import Tariff

    ec.Supplier.register(_SUPPLIER_KEY, ec.Supplier(products={_PRODUCT_KEY: Tariff(root=[])}))

# A second supplier that has a day_night_07 variant of the product.
_SUPPLIER_VARIANT_KEY = "test_supplier_variant"
_PRODUCT_VARIANT_KEY = f"{_PRODUCT_KEY}_day_night_07"
if _SUPPLIER_VARIANT_KEY not in dict(ec.Supplier.items()):
    from energy_cost import Tariff

    ec.Supplier.register(
        _SUPPLIER_VARIANT_KEY,
        ec.Supplier(products={_PRODUCT_KEY: Tariff(root=[]), _PRODUCT_VARIANT_KEY: Tariff(root=[])}),
    )


def _make_contract(
    ean: str, start: dt.datetime, end: dt.datetime | None = None, supplier_key: str = _SUPPLIER_KEY
) -> Contract:
    return Contract(
        ean=ean,
        customer_type=CustomerType.RESIDENTIAL,
        connection_type=ConnectionType.ELECTRICITY,
        supplier=NamedIdentifier(name="Test Supplier", id=supplier_key),
        product=NamedIdentifier(name="Test Product", id=_PRODUCT_KEY),
        distributor=NamedIdentifier(name="Fluvius Imewo", id="fluvius_imewo"),
        region=NamedIdentifier(name="Flanders", id="be_flanders"),
        start_date=start,
        end_date=end,
        last_invoice_date=None,
        is_green=False,
    )


class DummyMemberSourceSettings(MemberSourceSettings):
    type: str = "dummy_member_source"


class DummyMemberSource(MemberSource[Member], settings=DummyMemberSourceSettings):
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

    def test_response_is_list(self):
        response = self.client.get(self.prefix + "/1/contracts/EAN123")
        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 2

    def test_versions_have_start_date(self):
        response = self.client.get(self.prefix + "/1/contracts/EAN123")
        versions = response.json()
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

    def test_meter_type_without_variant_uses_base_product_key(self):
        """meter_type supplied but the supplier has no variant → product_key stays as-is."""
        response = self.client.get(self.prefix + "/1/contracts/EAN123?meter_type=day_night_06")
        assert response.status_code == 200
        for contract in response.json():
            assert contract["product_key"] == _PRODUCT_KEY

    def test_meter_type_with_variant_uses_variant_product_key(self):
        """meter_type supplied and the supplier has a matching variant → variant product_key is used."""
        source = DummyMemberSource()
        # Override contracts to use the variant supplier
        variant_contract = _make_contract(
            "EAN456",
            start=dt.datetime(2024, 1, 1, tzinfo=dt.UTC),
            supplier_key=_SUPPLIER_VARIANT_KEY,
        )
        source.members[0].addresses[0].contracts = [variant_contract]

        app = FastAPI()
        module = MembersModule(source=source, name="variant")
        app.include_router(module)
        client = TestClient(app)

        response = client.get(module.prefix + "/1/contracts/EAN456?meter_type=day_night_07")
        assert response.status_code == 200
        assert all(c["product_key"] == _PRODUCT_VARIANT_KEY for c in response.json())


def test_can_create_from_settings():
    module = MembersModule.create(
        {
            "type": "members",
            "source": {
                "type": "dummy_member_source",
            },
        }
    )

    assert isinstance(module, MembersModule)
    assert isinstance(module.source, DummyMemberSource)
    assert len(module.source.list()) == 2
