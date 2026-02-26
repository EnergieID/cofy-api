from os import environ

from fastapi import Depends
from sqlalchemy import create_engine

from cofy.cofy_api import CofyApi
from cofy.modules.members.module import MembersModule
from cofy.modules.members.sources.db_source import MembersDbSource
from cofy.modules.tariff.formats.kiwatt import KiwattFormat
from cofy.modules.tariff.module import TariffModule
from cofy.modules.tariff.sources.entsoe_day_ahead import EntsoeDayAheadTariffSource
from cofy.token_auth import token_verifier

# Database configuration
DB_URL = environ.get("DB_URL", "sqlite:///./demo.db")
DB_CONNECT_ARGS = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
engine = create_engine(DB_URL, connect_args=DB_CONNECT_ARGS)

# Initialize the Cofy API
cofy = CofyApi(dependencies=[Depends(token_verifier({environ.get("COFY_API_TOKEN"): {"name": "Demo User"}}))])

entsoe = TariffModule(
    settings={
        "api_key": environ.get("ENTSOE_API_KEY", ""),
        "name": "entsoe",
    }
)
cofy.register_module(entsoe)

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
cofy.register_module(kiwatt)

# members endpoint for Demo members, using a CSV file as source
cofy.register_module(MembersModule(settings={"source": MembersDbSource(engine), "name": "demo"}))

app = cofy
