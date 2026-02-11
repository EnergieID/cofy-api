from os import environ

from fastapi import Depends

from src.cofy.cofy_api import CofyApi
from src.cofy.token_auth import token_verifier
from src.modules.tariff.formats.kiwatt import KiwattFormat
from src.modules.tariff.module import TariffModule
from src.modules.tariff.sources.entsoe_day_ahead import EntsoeDayAheadTariffSource

app = CofyApi(
    dependencies=[
        Depends(token_verifier({environ.get("COFY_API_TOKEN"): {"name": "Demo User"}}))
    ]
)

entsoe = TariffModule(
    settings={
        "api_key": environ.get("ENTSOE_API_KEY", ""),
        "name": "entsoe",
    }
)
app.register_module(entsoe)

## Tariff app with custom source
source = EntsoeDayAheadTariffSource(
    country_code="NL",
    api_key=environ.get("ENTSOE_API_KEY", ""),
)
kiwatt = TariffModule(
    settings={
        "source": source,
        "name": "kiwatt",
        "formats": [
            KiwattFormat(),
        ],
    }
)
app.register_module(kiwatt)
