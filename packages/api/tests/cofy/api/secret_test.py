"""Secrets: named credentials, referenced by name from secret fields."""

import pytest
from pydantic import BaseModel, ValidationError

from cofy.api import CofyAPI, finalize
from cofy.api.cofy_api import CofyAPISettings
from cofy.api.secret import Secret, SecretRef, SecretSettings
from cofy.modules.discovery import discover_installed_types

discover_installed_types()


class Credentials(BaseModel):
    api_key: Secret


def secret(name: str) -> dict:
    return {"type": "secret", "name": name}


def entsoe_module(api_key: str = "entsoe_key") -> dict:
    return {"type": "tariff", "name": "prices", "source": {"type": "entsoe_day_ahead", "api_key": secret(api_key)}}


def config(modules: list[dict], secrets: list[dict]) -> dict:
    return {"type": "cofy_api", "modules": modules, "secrets": secrets}


# ── secret fields ─────────────────────────────────────────────────────────


def test_a_secret_field_holds_a_reference_to_a_secret():
    credentials = Credentials.model_validate({"api_key": secret("entsoe_key")})

    assert credentials.api_key == SecretRef(name="entsoe_key")
    assert credentials.model_dump() == {"api_key": secret("entsoe_key")}


def test_a_secret_field_takes_no_credential_itself():
    with pytest.raises(ValidationError):
        Credentials.model_validate({"api_key": "the-actual-key"})


def test_a_secret_field_rejects_a_reference_to_what_is_no_name():
    with pytest.raises(ValidationError):
        Credentials.model_validate({"api_key": secret("not a name!")})


def test_a_secret_field_is_described_as_a_reference_to_a_secret():
    schema = Credentials.model_json_schema()
    field = schema["$defs"][schema["properties"]["api_key"]["$ref"].split("/")[-1]]

    assert field["x-secret"] is True
    assert field["properties"]["type"]["const"] == "secret"
    # so a form labels it as the field it's in
    assert "title" not in field and "description" not in field


def test_a_secret_field_can_only_be_resolved_while_its_configuration_is_built():
    with pytest.raises(RuntimeError, match="while its configuration is built"):
        SecretRef(name="entsoe_key").convert()


# ── secrets ───────────────────────────────────────────────────────────────


def test_a_secret_value_is_only_revealed_when_written_to_disk():
    secret = SecretSettings.model_validate({"name": "entsoe_key", "value": "real"})

    assert "real" not in str(secret.model_dump())
    assert "real" not in secret.model_dump_json()
    assert "real" not in repr(secret)
    assert secret.model_dump(round_trip=True)["value"] == "real"


def test_a_secret_cannot_be_read_from_the_environment():
    """The environment holds the deployment's own secrets, which no community's config may reach."""
    with pytest.raises(ValidationError):
        SecretSettings.model_validate({"name": "a", "value": {"env": "ENTSOE_API_KEY"}})


# ── in a configuration ────────────────────────────────────────────────────


def test_a_configuration_gives_each_secret_field_the_value_of_the_secret_it_names():
    nl = entsoe_module("nl_key") | {"name": "nl"}

    cofy = CofyAPI.create(
        config(
            [entsoe_module(), nl],
            [{"name": "entsoe_key", "value": "be-key"}, {"name": "nl_key", "value": "nl-key"}],
        )
    )

    keys = {module.name: module.source.client.api_key for module in cofy.modules}
    assert keys == {"prices": "be-key", "nl": "nl-key"}


def test_a_secret_used_in_a_resource_is_given_to_it_too():
    cofy = CofyAPI.create(
        {
            "type": "cofy_api",
            "secrets": [{"name": "entsoe_key", "value": "real"}],
            "resources": [
                {
                    "type": "source",
                    "name": "prices",
                    "value": {"type": "entsoe_day_ahead", "api_key": {"type": "secret", "name": "entsoe_key"}},
                }
            ],
            "modules": [{"type": "tariff", "name": "spot", "source": {"type": "resource", "name": "prices"}}],
        }
    )

    assert cofy.modules[0].source.client.api_key == "real"


@pytest.mark.parametrize(
    ("modules", "secrets", "message"),
    [
        ([entsoe_module("missing")], [], "unknown secret 'missing'"),
        ([], [{"name": "a", "value": "x"}, {"name": "a", "value": "y"}], "'a' is used more than once"),
    ],
    ids=["unknown", "duplicate_name"],
)
def test_secrets_that_dont_fit_are_rejected(modules, secrets, message):
    finalize()
    with pytest.raises(ValidationError, match=message):
        CofyAPISettings.model_validate(config(modules, secrets))


def test_a_configuration_with_secrets_round_trips():
    finalize()
    settings = CofyAPISettings.model_validate(config([entsoe_module()], [{"name": "entsoe_key", "value": "real"}]))

    dumped = settings.model_dump(exclude_none=True, round_trip=True)

    assert dumped["modules"][0]["source"]["api_key"] == secret("entsoe_key")
    assert dumped["secrets"] == [{"name": "entsoe_key", "value": "real"}]
    assert CofyAPISettings.model_validate(dumped) == settings


def test_a_configuration_that_fails_validation_quotes_none_of_its_secrets():
    finalize()
    with pytest.raises(ValidationError) as error:
        CofyAPISettings.model_validate(
            config([entsoe_module("missing")], [{"name": "entsoe_key", "value": "SUPERSECRETVALUE123"}])
        )

    assert "unknown secret 'missing'" in str(error.value)
    assert "SUPERSECRETVALUE123" not in str(error.value)
