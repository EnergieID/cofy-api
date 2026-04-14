from os import environ
from pathlib import Path

from energy_cost import MeterType, Tariff
from energy_cost.data.be import distributors
from energy_cost.index import CSVIndex, EntsoeDayAheadIndex, Index
from fastapi import Depends
from isodate import Duration

from cofy import CofyAPI
from cofy.api import token_verifier
from cofy.modules.billing.module import BillingModule
from cofy.modules.directive import DirectiveModule, DirectiveSource
from cofy.modules.members import MembersFileSource, MembersModule
from cofy.modules.production import EnergyIDProduction, ProductionModule
from cofy.modules.tariff import EnergyCostTariffSource, EntsoeDayAheadTariffSource, KiwattFormat, TariffModule
from demo.members.load_from_csv import example_load_members_from_file

DATA_DIR = Path(__file__).resolve().parent / "data"

# Initialize the Cofy API
cofy = CofyAPI(dependencies=[Depends(token_verifier({environ.get("COFY_API_TOKEN"): {"name": "Demo User"}}))])

entsoe = TariffModule(
    source=EntsoeDayAheadTariffSource(
        api_key=environ.get("ENTSOE_API_KEY", ""),
    ),
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

## Tariff app with EnergyCost as source
Index.register("Belpex15min", EntsoeDayAheadIndex("BE", api_key=environ.get("ENTSOE_API_KEY", "")))
TARIFF_CONFIG_PATH = str(DATA_DIR / "dynamic_tariff.yaml")
dynamic_tariff = TariffModule(
    source=EnergyCostTariffSource(yaml_config=TARIFF_CONFIG_PATH, meter_type=MeterType.SINGLE_RATE),
    name="dynamic",
    description="Our dynamic tariff tracking the Belpex.",
)
cofy.register_module(dynamic_tariff)

## Billing app for our tariff
Index.register("BelMonthly", CSVIndex(str(DATA_DIR / "monthly_index.csv"), resolution=Duration(months=1)))
billing = BillingModule(
    products={
        "fixed": Tariff.from_yaml(str(DATA_DIR / "fixed_tariff.yaml")),
        "variable": Tariff.from_yaml(str(DATA_DIR / "variable_tariff.yaml")),
        "dynamic": Tariff.from_yaml(TARIFF_CONFIG_PATH),
    },
    distributors=distributors,
)
cofy.register_module(billing)

## Production app with EnergyID as source
wind = ProductionModule(
    source=EnergyIDProduction(
        api_key=environ.get("ENERGY_ID_API_KEY", ""),
        record_id=environ.get("ENERGY_ID_RECORD_ID", ""),
    ),
    name="wind",
)
cofy.register_module(wind)

# members endpoint for Demo members, using a CSV file as source
CSV_PATH = str(DATA_DIR / "members_example.csv")
cofy.register_module(
    MembersModule(
        source=MembersFileSource(CSV_PATH, example_load_members_from_file),
        name="demo",
    )
)

# a directive module based on the entsoe day-ahead prices, with custom boundaries
directive = DirectiveModule(
    source=DirectiveSource(
        source=entsoe.source,
        boundaries=(0, 10, 25, 50),
        reverse=True,  # now low is good and high is bad, the opposite of the default behavior
    ),
    name="entsoe",
    description="A directive module based on the entsoe day-ahead prices, with custom boundaries.",
)
cofy.register_module(directive)


app = cofy
