from energy_cost import PowerDirection
from fastapi import HTTPException

from cofy.api.module import Module, ModuleSettings

from .models.billing_request import BillingRequest
from .models.billing_response import BillingMetadata, BillingResponse


class BillingModuleSettings(ModuleSettings):
    type: str = "billing"


class BillingModule(Module, settings=BillingModuleSettings):
    type: str = "billing"
    type_description: str = "Module that computes energy costs based on meter data and contract information."

    def init_routes(self):
        def calculate_cost(body: BillingRequest) -> BillingResponse:
            try:
                df = body.contract.apply(
                    consumption=body.consumption.to_meter(PowerDirection.CONSUMPTION),
                    injection=body.injection.to_meter(PowerDirection.INJECTION) if body.injection is not None else None,
                    start=body.start,
                    end=body.end,
                    output_resolution=body.resolution,
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

    @property
    def version(self) -> str:
        return "v2"
