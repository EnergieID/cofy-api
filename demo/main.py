from os import environ
from pathlib import Path

from energy_cost.index import EntsoeDayAheadIndex, Index
from energy_cost.tariff import MeterType
from fastapi import Depends

from cofy import CofyApi
from cofy.api import token_verifier
from cofy.modules.directive import DirectiveModule, DirectiveSource
from cofy.modules.members import MembersCSVSource, MembersModule
from cofy.modules.production import EnergyIDProduction, ProductionModule
from cofy.modules.tariff import EnergyCostTariffSource, EntsoeDayAheadTariffSource, KiwattFormat, TariffModule

DATA_DIR = Path(__file__).resolve().parent / "data"

# Initialize the Cofy API
cofy = CofyApi(dependencies=[Depends(token_verifier({environ.get("COFY_API_TOKEN"): {"name": "Demo User"}}))])

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
TARIFF_CONFIG_PATH = str(DATA_DIR / "energy_cost_tariff.yaml")
dynamic_tariff = TariffModule(
    source=EnergyCostTariffSource(yaml_config=TARIFF_CONFIG_PATH, meter_type=MeterType.SINGLE_RATE),
    name="dynamic",
    description="Our dynamic tariff tracking the Belpex.",
)
cofy.register_module(dynamic_tariff)

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
        source=MembersCSVSource(
            CSV_PATH,
            id_field="KLANTNUMMER",
            email_field="EMAIL",
            activation_code_field="ACTIVATIECODE",
        ),
        name="demo",
    )
)

# a directive module based on the entsoe day-ahead prices, with custom boundries
directive = DirectiveModule(
    source=DirectiveSource(
        source=entsoe.source,
        boundries=(0, 10, 25, 50),
    ),
    name="entsoe",
    description="A directive module based on the entsoe day-ahead prices, with custom boundries.",
)
cofy.register_module(directive)


app = cofy
