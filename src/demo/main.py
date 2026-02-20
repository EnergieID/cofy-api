from os import environ

from fastapi import Depends
from sqlalchemy import create_engine

from src.cofy.cofy_api import CofyApi
from src.cofy.token_auth import token_verifier
from src.modules.members.module import MembersModule
from src.modules.members.sources.db_source import MembersDbSource
from src.modules.tariff.module import TariffModule
from src.modules.tariff.sources.entsoe_day_ahead import EntsoeDayAheadTariffSource

# Database configuration
DB_URL = environ.get("DB_URL", "sqlite:///./demo.db")
DB_CONNECT_ARGS = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
engine = create_engine(DB_URL, connect_args=DB_CONNECT_ARGS)

# Initialize the Cofy API
cofy = CofyApi(
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
    ],
)

tariffs = TariffModule(settings={"api_key": environ.get("ENTSOE_API_KEY", "")})
cofy.register_module(tariffs)

## Tariff app with custom source
source = EntsoeDayAheadTariffSource(
    country_code="NL",
    api_key=environ.get("ENTSOE_API_KEY", ""),
)
nl_tariffs = TariffModule(settings={"source": source, "name": "nl_tariffs"})
cofy.register_module(nl_tariffs)

## Tariff app with default source and custom settings
fr_tariffs = TariffModule(
    settings={
        "country_code": "FR",
        "api_key": environ.get("ENTSOE_API_KEY", ""),
        "name": "fr_tariffs",
        "description": "Entsoe tariff data for France",
        "display_name": "French Tariffs",
    },
)
cofy.register_module(fr_tariffs)

# members endpoint for EnergyBar members, using a CSV file as source
cofy.register_module(
    MembersModule(settings={"source": MembersDbSource(engine), "name": "energybar"})
)

app = cofy
