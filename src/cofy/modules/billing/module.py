from cofy.api.module import Module

from .models.billing_request import BillingRequest
from .models.billing_response import BillingMetadata, BillingResponse


class BillingModule(Module):
    type: str = "billing"
    type_description: str = "Module that computes energy costs based on meter data and contract information."

    def __init__(self, *, default_region: str = "be_flanders", default_supplier: str | None = None, **kwargs):
        self.default_region = default_region
        self.default_supplier = default_supplier
        super().__init__(**kwargs)

    def init_routes(self):
        def calculate_cost(body: BillingRequest) -> BillingResponse:  # ty: ignore[invalid-type-form]
            contract = body.contract.to_contract(
                default_region=self.default_region, default_supplier=self.default_supplier
            )
            meters = [m.to_meter() for m in body.meters]

            try:
                df = contract.apply(
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
