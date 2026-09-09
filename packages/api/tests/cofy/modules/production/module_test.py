from cofy.api.module import Module
from cofy.modules.production import ProductionModule


def test_can_create_from_settings():
    module = Module.create(
        {
            "type": "production",
            "source": {
                "type": "energyid_production",
                "api_key": "dummy-key",
                "record_id": "dummy-record",
            },
        }
    )

    assert isinstance(module, ProductionModule)
