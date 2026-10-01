from cofy.api.module import Module
from cofy.modules.production import ProductionModule
from tests.cofy.secrets import with_secrets


def test_can_create_from_settings():
    with with_secrets(energyid_key="dummy-key"):
        module = Module.create(
            {
                "type": "production",
                "source": {
                    "type": "energyid_production",
                    "api_key": {"type": "secret", "name": "energyid_key"},
                    "record_id": "dummy-record",
                },
            }
        )

    assert isinstance(module, ProductionModule)
