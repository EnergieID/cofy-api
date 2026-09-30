import os
from pathlib import Path

import yaml
from energy_cost.index import CachedEntsoeDayAheadIndex, CSVIndex, Index
from isodate import Duration

from cofy.api import CofyAPI
from cofy.modules.discovery import discover_all_types

# Register every installed module, source and format type, so the settings can use any of them.
discover_all_types()

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
