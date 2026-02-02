import json

from fastapi import Depends

from src.cofy.cofy_api import CofyApi
from src.cofy.token_auth import token_verifier
from src.modules.tariff.app import TariffApp
from src.modules.tariff.sources.entsoe_day_ahead import EntsoeDayAheadTariffSource

with open("local.settings.json") as f:
    environment = json.load(f)

app = CofyApi(
    dependencies=[
        Depends(
            token_verifier(
                {
                    "foo": {"name": "Demo Token", "expires": "2030-12-31T23:59:59"},
                    "bar": {
                        "name": "Expired Token",
                        "expires": "2020-01-01T00:00:00",
                    },
                    "bas": {"name": "Infinity Token"},
                }
            )
        )
    ]
)

tariffs = TariffApp(settings={"api_key": environment.get("ENTSOE_API_KEY", "")})
app.register_module(tariffs)

## Tariff app with custom source
source = EntsoeDayAheadTariffSource(
    country_code="NL",
    api_key=environment.get("ENTSOE_API_KEY", ""),
)
nl_tariffs = TariffApp(settings={"source": source, "name": "nl_tariffs"})
app.register_module(nl_tariffs)

## Tariff app with default source and custom settings
fr_tariffs = TariffApp(
    settings={
        "country_code": "FR",
        "api_key": environment.get("ENTSOE_API_KEY", ""),
        "name": "fr_tariffs",
    },
)
app.register_module(fr_tariffs)
