from energy_cost import Tariff

from cofy.api.module import Module


class BillingModule(Module):
    type: str = "billing"
    type_description: str = "Module that computes energy costs based on meter data and contract information."

    def __init__(self, *, products: dict[str, Tariff], distributors: dict[str, Tariff], **kwargs):
        self.products: dict[str, Tariff] = products
        self.distributors: dict[str, Tariff] = distributors
        super().__init__(**kwargs)

    def init_routes(self):
        pass
