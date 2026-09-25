import os
from pathlib import Path

import yaml
from energy_cost.index import CachedEntsoeDayAheadIndex, CSVIndex, Index
from isodate import Duration

# Import concrete modules/sources/formats so they register for FromSettingsMixin.create.
from cofy.api import CofyAPI, TokenAuth  # noqa: F401
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
SETTINGS_PATH = Path(__file__).resolve().parent / "settings.yaml"

# Pre-register indexes used by tariff and billing flows.
Index.register("Belpex15min", CachedEntsoeDayAheadIndex("BE", api_key=os.environ.get("ENTSOE_API_KEY", "")))
Index.register("BelMonthly", CSVIndex(str(DATA_DIR / "monthly_index.csv"), resolution=Duration(months=1)))

# `${VAR}` placeholders in the settings file are filled in from the environment before parsing,
# so secrets stay out of the committed config.
settings = yaml.safe_load(os.path.expandvars(SETTINGS_PATH.read_text()))
cofy = CofyAPI.create(settings)

app = cofy
