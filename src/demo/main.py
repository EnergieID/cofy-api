from contextlib import asynccontextmanager
from importlib import resources
from os import environ

from fastapi import Depends

from src.cofy.cofy_api import CofyApi
from src.cofy.db.cofy_db import CofyDB
from src.cofy.token_auth import token_verifier
from src.modules.members.module import MembersModule
from src.modules.members.sources.eb_db_source import EBDbSource
from src.modules.tariff.module import TariffModule
from src.modules.tariff.sources.entsoe_day_ahead import EntsoeDayAheadTariffSource

SQLITE_URL = f"sqlite:///{resources.files('src.demo.db').joinpath('database.db')}"


@asynccontextmanager
async def lifespan(app: CofyApi):
    # Startup code
    app.db.run_migrations()
    yield
    # Shutdown code (if needed)


cofy = CofyApi(
    db=CofyDB(
        db_url=SQLITE_URL, engine_kwargs={"connect_args": {"check_same_thread": False}}
    ),
    lifespan=lifespan,
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
    },
)
cofy.register_module(fr_tariffs)

# members endpoint for EnergyBar members, using a CSV file as source
cofy.register_module(
    MembersModule(settings={"source": EBDbSource(cofy.db.engine), "name": "energybar"})
)

app = cofy
