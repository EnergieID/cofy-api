from os import environ

from fastapi import Depends
from sqlalchemy import create_engine

from src.cofy.cofy_api import CofyApi
from src.cofy.token_auth import token_verifier
from src.modules.members.module import MembersModule
from src.modules.members.sources.db_source import MembersDbSource
from src.modules.production.module import ProductionModule
from src.modules.production.sources.energyID_production import EnergyIDProduction
from src.modules.tariff.formats.kiwatt import KiwattFormat
from src.modules.tariff.module import TariffModule
from src.modules.tariff.sources.entsoe_day_ahead import EntsoeDayAheadTariffSource

# Database configuration
DB_URL = environ.get("DB_URL", "sqlite:///./demo.db")
DB_CONNECT_ARGS = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
engine = create_engine(DB_URL, connect_args=DB_CONNECT_ARGS)

# Initialize the Cofy API
cofy = CofyApi(dependencies=[Depends(token_verifier({environ.get("COFY_API_TOKEN"): {"name": "Demo User"}}))])

entsoe = TariffModule(
    api_key=environ.get("ENTSOE_API_KEY", ""),
    name="entsoe",
)
cofy.register_module(entsoe)

## Tariff app with custom source
source = EntsoeDayAheadTariffSource(
    country_code="NL",
    api_key=environ.get("ENTSOE_API_KEY", ""),
)
kiwatt = TariffModule(
    source=source,
    name="kiwatt",
    formats=[
        KiwattFormat(),
    ],
)
cofy.register_module(kiwatt)

wind = ProductionModule(
    source=EnergyIDProduction(
        api_key=environ.get("ENERGY_ID_API_KEY", ""),
        record_id=environ.get("ENERGY_ID_RECORD_ID", ""),
    ),
    name="wind",
    supported_resolutions=EnergyIDProduction.SUPPORTED_RESOLUTIONS,
)
cofy.register_module(wind)

# members endpoint for Demo members, using a CSV file as source
cofy.register_module(MembersModule(source=MembersDbSource(engine), name="demo"))

app = cofy
