import json

from src.cofy.app import Cofy
from src.modules.tariff.app import TariffApp
from src.modules.tariff.sources.entsoe_day_ahead import EntsoeDayAheadTariffSource

with open("local.settings.json") as f:
    environment = json.load(f)

cofy = Cofy(settings={})

tariffs = TariffApp(settings={"api_key": environment.get("ENTSOE_API_KEY", "")})
cofy.register_module(tariffs)

## Tariff app with custom source
source = EntsoeDayAheadTariffSource(
    country_code="NL",
    api_key=environment.get("ENTSOE_API_KEY", ""),
)
nl_tariffs = TariffApp(settings={"source": source, "name": "nl_tariffs"})
cofy.register_module(nl_tariffs)

## Tariff app with default source and custom settings
fr_tariffs = TariffApp(
    settings={
        "country_code": "FR",
        "api_key": environment.get("ENTSOE_API_KEY", ""),
        "name": "fr_tariffs",
    },
)
cofy.register_module(fr_tariffs)

app = cofy.fastApi
