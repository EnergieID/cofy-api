from os import environ

from fastapi import Depends

from src.cofy.cofy_api import CofyApi
from src.cofy.token_auth import token_verifier
from src.modules.tariff.formats.kiwatt import KiwattFormat
from src.modules.tariff.module import TariffModule
from src.modules.tariff.sources.entsoe_day_ahead import EntsoeDayAheadTariffSource

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

tariffs = TariffModule(settings={"api_key": environ.get("ENTSOE_API_KEY", "")})
app.register_module(tariffs)

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
