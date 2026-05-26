from fastapi import HTTPException

from cofy.api.module import Module

from .models.billing_request import BillingRequest
from .models.billing_response import BillingMetadata, BillingResponse


class BillingModule(Module):
    type: str = "billing"
    type_description: str = "Module that computes energy costs based on meter data and contract information."

    def init_routes(self):
        def calculate_cost(body: BillingRequest) -> BillingResponse:
            meters = [m.to_meter() for m in body.meters]

            try:
                df = body.contract.apply(
                    meters=meters,
                    start=body.start,
                    end=body.end,
                    resolution=body.resolution,
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e

            if df is None:
                raise HTTPException(status_code=400, detail="No cost data could be calculated for the given period.")

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
