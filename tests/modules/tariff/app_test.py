import pytest
from fastapi import APIRouter

from src.modules.tariff.app import TariffApp
from src.modules.tariff.sources.entsoe_day_ahead import EntsoeDayAheadTariffSource
from tests.modules.tariff.dummy_source import DummySource


class DummyAPI:
    router = "dummy_router"


@pytest.mark.parametrize(
    "settings, expected_source_type",
    [
        ({"source": DummySource()}, DummySource),
        ({"country_code": "DE", "api_key": "key"}, EntsoeDayAheadTariffSource),
    ],
)
def test_tariffapp_source_selection(settings, expected_source_type):
    app = TariffApp(settings)
    assert isinstance(app.source, expected_source_type)


def test_tariffapp_router_property():
    app = TariffApp({"country_code": "DE", "api_key": "key"})
    router = app.router
    assert isinstance(router, APIRouter)


def test_tariffapp_type_property():
    app = TariffApp({"country_code": "DE", "api_key": "key"})
    assert app.type == "tariff"
