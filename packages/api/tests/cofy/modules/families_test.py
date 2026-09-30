"""The source and format families decide which combinations can be configured."""

import pytest
from pydantic import TypeAdapter, ValidationError

from cofy.api import finalize
from cofy.api.module import ModuleSettings
from cofy.modules.directive import BoundarySourceSettings, DirectiveSource
from cofy.modules.discovery import discover_installed_types
from cofy.modules.tariff import PriceSource
from cofy.modules.timeseries import NumericSource, TimeseriesSourceSettings

discover_installed_types()

ENTSOE = {"type": "entsoe_day_ahead", "api_key": "key"}
ENERGYID = {"type": "energyid_production", "api_key": "key", "record_id": "record"}
ACC = {"type": "acc_forecast", "ean": "541", "credentials": "{}"}


def cached(source: dict) -> dict:
    return source | {"cache": {"max_age": "PT1H"}}


def directive(source: dict) -> dict:
    return {"type": "directive", "boundaries": [0, 1, 2, 3], "source": source}


def module(module_type: str, source: dict, formats: list[dict] | None = None) -> dict:
    return {"type": module_type, "source": source} | ({"formats": formats} if formats is not None else {})


def validate(data: dict):
    finalize()
    return TypeAdapter(ModuleSettings.union_type()).validate_python(data)


def source_branches(module_type: str) -> set[str]:
    finalize()
    schema = ModuleSettings.registry()[module_type].model_json_schema()
    value, _ref = schema["properties"]["source"]["oneOf"]
    return set(value["discriminator"]["mapping"])


@pytest.mark.parametrize(
    "data",
    [
        module("tariff", ENTSOE),
        module("tariff", cached(ENTSOE), formats=[{"type": "kiwatt"}, {"type": "json"}]),
        module("production", cached(ENERGYID)),
        module("directive", directive(cached(ENTSOE)), formats=[{"type": "directive"}, {"type": "csv"}]),
        module(
            "directive",
            directive(cached({"type": "acc_simultaneity", "cluster": {"type": "pool", "members": [{"source": ACC}]}})),
        ),
        module("simultaneity", {"type": "simultaneity", "sources": [cached(ACC)]}),
    ],
    ids=[
        "tariff_entsoe",
        "tariff_cached_with_price_formats",
        "production_energyid",
        "directive_of_price",
        "directive_of_acc_simultaneity",
        "simultaneity_of_net_volumes",
    ],
)
def test_valid_combinations_are_accepted(data):
    validate(data)


@pytest.mark.parametrize(
    "data",
    [
        module("tariff", ENERGYID),
        module("tariff", cached(ENERGYID)),
        module("production", directive(ENERGYID)),
        module("directive", directive(directive(ENTSOE))),
        module("directive", directive(cached(directive(ENTSOE)))),
        module("simultaneity", {"type": "simultaneity", "sources": [ENTSOE]}),
        module(
            "simultaneity", {"type": "acc_simultaneity", "cluster": {"type": "pool", "members": [{"source": ENERGYID}]}}
        ),
        module("tariff", ENTSOE, formats=[{"type": "directive"}]),
        module("production", ENERGYID, formats=[{"type": "kiwatt"}]),
    ],
    ids=[
        "production_as_price",
        "cached_production_as_price",
        "directive_as_production",
        "directive_of_directive",
        "directive_of_cached_directive",
        "price_as_net_volume",
        "production_as_acc_member",
        "directive_format_for_prices",
        "price_format_for_production",
    ],
)
def test_invalid_combinations_are_rejected(data):
    with pytest.raises(ValidationError):
        validate(data)


def test_a_module_only_offers_the_sources_of_its_family():
    assert source_branches("tariff") == {"entsoe_day_ahead", "energy_cost"}
    assert source_branches("production") == {"energyid_production"}
    assert source_branches("simultaneity") == {"simultaneity", "acc_simultaneity"}
    assert source_branches("directive") == {"directive", "dynamic_boundary_directive"}


def test_a_cached_source_is_still_a_member_of_its_family():
    source = NumericSource.create(cached(ENTSOE))

    assert isinstance(source, PriceSource)
    assert source.cache is not None


def test_the_boundary_family_has_nothing_to_offer_yet():
    assert BoundarySourceSettings.registry() == {}


def test_the_root_family_holds_every_source():
    assert {"entsoe_day_ahead", "energyid_production", "acc_forecast", "directive"} <= set(
        TimeseriesSourceSettings.registry()
    )


def test_a_directive_source_is_built_from_a_numeric_source():
    source = DirectiveSource.create(directive(cached(ENTSOE)))

    assert isinstance(source.source, NumericSource)
