from energy_cost import Tariff

from cofy.api.module import Module

from .models.billing_request import make_billing_request_model
from .models.billing_response import BillingMetadata, BillingResponse


class BillingModule(Module):
    type: str = "billing"
    type_description: str = "Module that computes energy costs based on meter data and contract information."

    def __init__(self, *, products: dict[str, Tariff], distributors: dict[str, Tariff], **kwargs):
        self.products: dict[str, Tariff] = products
        self.distributors: dict[str, Tariff] = distributors
        super().__init__(**kwargs)

    def init_routes(self):
        BillingRequestModel = make_billing_request_model(self.products, self.distributors)

        async def calculate_cost(body: BillingRequestModel) -> BillingResponse:  # ty: ignore[invalid-type-form]
            contract = body.contract.to_contract()
            meters = [m.to_meter() for m in body.meters]

            try:
                df = contract.calculate_cost(
                    meters=meters,
                    start=body.start,
                    end=body.end,
                    resolution=body.resolution,
                )
            except ValueError as e:
                from fastapi import HTTPException

                raise HTTPException(status_code=400, detail=str(e)) from e

            return BillingResponse.from_df(
                df,
                BillingMetadata(
                    start=body.start,
                    end=body.end,
                    resolution=body.resolution,
                ),
            )

        self.add_api_route(
            "",
            calculate_cost,
            methods=["POST"],
            response_model=BillingResponse,
            summary="Calculate energy cost",
        )
