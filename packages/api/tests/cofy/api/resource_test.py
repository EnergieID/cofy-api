from typing import Literal

import pytest
from pydantic import ValidationError

from cofy.api import BaseSettingsModel, CofyAPI, FromSettingsMixin, RefSettings, finalize
from cofy.api.cofy_api import CofyAPISettings
from cofy.api.module import ModuleSettings
from cofy.modules.discovery import discover_installed_types

discover_installed_types()

TARIFF = [{"start": "2024-01-01T00:00:00+01:00", "consumption": {"constant_cost": 10.0}}]


def ref(name: str) -> dict:
    return {"type": "resource", "name": name}


def entsoe(api_key: str = "key", country_code: str = "BE") -> dict:
    return {"type": "entsoe_day_ahead", "api_key": {"type": "secret", "name": api_key}, "country_code": country_code}


def config(modules: list[dict], resources: list[dict]) -> dict:
    secrets = [{"name": "key", "value": "real-key"}, {"name": "empty", "value": ""}]
    return {"type": "cofy_api", "modules": modules, "resources": resources, "secrets": secrets}


def module(module_type: str, name: str, source: dict) -> dict:
    return {"type": module_type, "name": name, "source": source}


def create(data: dict) -> CofyAPI:
    return CofyAPI.create(data)


def module_named(cofy: CofyAPI, name: str):
    return next(module for module in cofy.modules if module.name == name)


def test_a_source_resource_is_built_once_and_shared_by_every_reference():
    cofy = create(
        config(
            [
                module("tariff", "prices", ref("day_ahead")),
                module(
                    "directive", "signal", {"type": "directive", "boundaries": [0, 1, 2, 3], "source": ref("day_ahead")}
                ),
            ],
            [
                {
                    "type": "source",
                    "name": "day_ahead",
                    "value": entsoe() | {"cache": {"max_age": "PT1H"}},
                }
            ],
        )
    )

    shared = module_named(cofy, "prices").source
    assert module_named(cofy, "signal").source.source is shared
    assert shared.cache is not None


def test_an_unreferenced_resource_is_not_built():
    create(config([], [{"type": "source", "name": "unused", "value": entsoe(api_key="empty")}]))  # would raise if built


def test_a_tariff_resource_fills_every_tariff_referencing_it():
    cofy = create(
        config(
            [module("tariff", "dynamic", {"type": "energy_cost", "tariff": ref("dynamic_tariff")})],
            [{"type": "tariff", "name": "dynamic_tariff", "value": TARIFF}],
        )
    )

    tariff = module_named(cofy, "dynamic").source.tariff
    assert type(tariff).__name__ == "Tariff"


def test_a_reference_accepts_a_resource_holding_any_member_of_its_family():
    """A directive takes any numeric source, so a resource holding prices fits it."""
    create(
        config(
            [module("directive", "signal", {"type": "directive", "boundaries": [0, 1, 2, 3], "source": ref("prices")})],
            [{"type": "source", "name": "prices", "value": entsoe()}],
        )
    )


@pytest.mark.parametrize(
    ("modules", "resources", "message"),
    [
        ([module("tariff", "prices", ref("missing"))], [], "unknown resource 'missing'"),
        (
            [module("tariff", "prices", ref("wind"))],
            [
                {
                    "type": "source",
                    "name": "wind",
                    "value": {
                        "type": "energyid_production",
                        "api_key": {"type": "secret", "name": "key"},
                        "record_id": "r",
                    },
                }
            ],
            "'wind' holds a energyid_production source, where one of energy_cost, entsoe_day_ahead is expected",
        ),
        (
            [module("tariff", "prices", ref("dynamic"))],
            [{"type": "tariff", "name": "dynamic", "value": TARIFF}],
            "is a tariff",
        ),
        (
            [],
            [{"type": "source", "name": "a", "value": entsoe()}, {"type": "source", "name": "a", "value": entsoe()}],
            "'a' is used more than once",
        ),
        (
            [],
            [
                {
                    "type": "source",
                    "name": "a",
                    "value": ref("b"),
                },
                {
                    "type": "source",
                    "name": "b",
                    "value": ref("a"),
                },
            ],
            "cycle: a -> b -> a",
        ),
    ],
    ids=["unknown", "wrong_family", "wrong_kind", "duplicate_name", "cycle"],
)
def test_references_that_dont_fit_a_resource_are_rejected(modules, resources, message):
    finalize()
    with pytest.raises(ValidationError, match=message):
        CofyAPISettings.model_validate(config(modules, resources))


def test_a_reference_can_only_be_resolved_while_its_configuration_is_built():
    with pytest.raises(RuntimeError, match="while its configuration is built"):
        RefSettings(name="anything").convert()


def test_a_configuration_with_references_round_trips():
    finalize()
    data = config(
        [module("tariff", "prices", ref("day_ahead"))],
        [{"type": "source", "name": "day_ahead", "value": entsoe()}],
    )
    settings = CofyAPISettings.model_validate(data)

    dumped = settings.model_dump(exclude_none=True, round_trip=True)
    assert dumped["modules"][0]["source"] == ref("day_ahead")
    assert dumped["resources"][0]["value"]["api_key"] == {"type": "secret", "name": "key"}
    assert CofyAPISettings.model_validate(dumped) == settings


def test_a_reference_tells_which_kinds_of_resource_it_accepts():
    finalize()
    tariff = ModuleSettings.registry()["tariff"].model_json_schema()
    directive = ModuleSettings.registry()["directive"].model_json_schema()

    assert tariff["properties"]["source"]["x-referable"] == {
        "kind": "source",
        "types": ["energy_cost", "entsoe_day_ahead"],
    }
    numeric = directive["$defs"]["DirectiveSourceSettings"]["properties"]["source"]["x-referable"]
    assert numeric["kind"] == "source"
    assert {"entsoe_day_ahead", "energyid_production", "acc_forecast", "simultaneity"} <= set(numeric["types"])
    assert "directive" not in numeric["types"]


def test_a_resource_referencing_another_one_fits_where_the_one_it_ends_at_fits():
    finalize()
    wind = {
        "type": "source",
        "name": "wind",
        "value": {"type": "energyid_production", "api_key": {"type": "secret", "name": "key"}, "record_id": "r"},
    }
    alias = {"type": "source", "name": "alias", "value": ref("prices")}
    prices = {"type": "source", "name": "prices", "value": entsoe()}

    CofyAPISettings.model_validate(config([module("tariff", "spot", ref("alias"))], [alias, prices]))
    with pytest.raises(ValidationError, match="'alias' holds a energyid_production source"):
        CofyAPISettings.model_validate(
            config([module("tariff", "spot", ref("alias"))], [alias | {"value": ref("wind")}, wind])
        )


def test_a_referable_field_stays_one_after_a_type_registers_late():
    """Registering more types rebuilds every field; a referable one must come out referable once, not twice."""
    finalize()

    class LateRegisteredSettings(BaseSettingsModel):
        type: Literal["late_registered"] = "late_registered"

    class LateRegistered(FromSettingsMixin, settings=LateRegisteredSettings):
        pass

    finalize()
    source = ModuleSettings.registry()["tariff"].model_json_schema()["properties"]["source"]
    value, ref = source["oneOf"]

    assert source["x-referable"]["kind"] == "source"
    assert set(value["discriminator"]["mapping"]) == {"energy_cost", "entsoe_day_ahead"}
    assert ref == {"$ref": "#/$defs/RefSettings"}
