from os import environ
from pathlib import Path

from energy_cost import Tariff
from energy_cost.index import CachedEntsoeDayAheadIndex, CSVIndex, Index
from isodate import Duration

from cofy import CofyAPI

# Import concrete modules/sources/formats so they register for FromSettingsMixin.create.
from cofy.api import TokenAuth  # noqa: F401
from cofy.modules.billing import BillingModule  # noqa: F401
from cofy.modules.directive import DirectiveFormat, DirectiveModule, DirectiveSource  # noqa: F401
from cofy.modules.production import EnergyIDProduction, ProductionModule  # noqa: F401
from cofy.modules.tariff import (  # noqa: F401
    EnergyCostTariffSource,
    EntsoeDayAheadTariffSource,
    KiwattFormat,
    TariffModule,
)

DATA_DIR = Path(__file__).resolve().parent / "data"

# Pre-register indexes used by tariff and billing flows.
Index.register("Belpex15min", CachedEntsoeDayAheadIndex("BE", api_key=environ.get("ENTSOE_API_KEY", "")))
Index.register("BelMonthly", CSVIndex(str(DATA_DIR / "monthly_index.csv"), resolution=Duration(months=1)))
TARIFF_CONFIG_PATH = str(DATA_DIR / "dynamic_tariff.yaml")


cofy = CofyAPI.create(
    {
        "type": "cofy_api",
        "debug_mode": True,
        "auth": {
            "type": "token",
            "tokens": {
                environ.get("COFY_API_TOKEN", ""): {
                    "name": "Demo User",
                }
            },
        },
        "modules": [
            {
                "type": "tariff",
                "name": "entsoe",
                "source": {
                    "type": "entsoe_day_ahead",
                    "api_key": environ.get("ENTSOE_API_KEY", ""),
                },
            },
            {
                "type": "tariff",
                "name": "kiwatt",
                "source": {
                    "type": "entsoe_day_ahead",
                    "country_code": "NL",
                    "api_key": environ.get("ENTSOE_API_KEY", ""),
                },
                "formats": [
                    {
                        "type": "kiwatt",
                    }
                ],
            },
            {
                "type": "tariff",
                "name": "dynamic",
                "description": "Our dynamic tariff tracking the Belpex.",
                "source": {
                    "type": "energy_cost",
                    "tariff": Tariff.from_yaml(TARIFF_CONFIG_PATH),
                },
            },
            {
                "type": "billing",
            },
            {
                "type": "production",
                "name": "wind",
                "source": {
                    "type": "energyid_production",
                    "api_key": environ.get("ENERGY_ID_API_KEY", ""),
                    "record_id": environ.get("ENERGY_ID_RECORD_ID", ""),
                },
            },
            {
                "type": "directive",
                "name": "entsoe",
                "description": "A directive module based on the entsoe day-ahead prices, with custom boundaries.",
                "source": {
                    "type": "directive",
                    "source": {
                        "type": "entsoe_day_ahead",
                        "api_key": environ.get("ENTSOE_API_KEY", ""),
                    },
                    "boundaries": [0, 10, 25, 50],
                    "reverse": True,
                },
                "formats": [
                    {
                        "type": "directive",
                    }
                ],
            },
        ],
    }
)

app = cofy
