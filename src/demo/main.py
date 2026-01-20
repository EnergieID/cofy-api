import json
from src.modules.tariff.app import TariffApp
from src.cofy.app import Cofy

environment = json.load(open("local.settings.json"))

cofy = Cofy(settings={})

tariffs = TariffApp(settings={"api_key": environment.get("ENTSOE_API_KEY", "")})
cofy.register_module(tariffs)

app = cofy.fastApi
