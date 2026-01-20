from src.modules.tariff.app import TariffApp
from src.cofy.app import Cofy


cofy = Cofy(settings={})

tariffs = TariffApp(settings={})
cofy.register_module(tariffs)

app = cofy.api
