import math
from typing import Any

import pandas as pd
from energy_cost import Tariff

from cofy.api.module import Module

from .models.billing_request import make_billing_request_model
from .models.billing_response import BillingDataPoint, BillingMetadata, BillingResponse


def _df_to_nested_list(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame with MultiIndex columns to a list of nested dicts.

    The timestamp column (added back via ``reset_index``) is lifted to a top-level
    key.  All other columns, which carry tuple keys from the MultiIndex, are
    converted to nested dicts that mirror the MultiIndex hierarchy.

    NaN values are converted to ``None`` (JSON ``null``).
    """
    result = []
    for _, row in df.iterrows():
        point: dict[str, Any] = {}
        for col, raw_value in row.items():
            value = None if (isinstance(raw_value, float) and math.isnan(raw_value)) else raw_value

            if isinstance(col, tuple):
                # Strip empty-string padding that reset_index adds to MultiIndex columns
                # e.g. ("timestamp", "", "") → ("timestamp",)
                key_parts = tuple(k for k in col if k != "")
                if len(key_parts) == 1:
                    point[str(key_parts[0])] = value
                else:
                    d = point
                    for k in key_parts[:-1]:
                        d = d.setdefault(k, {})
                    d[str(key_parts[-1])] = value
            else:
                point[str(col)] = value
        result.append(point)
    return result


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
                df: pd.DataFrame = contract.calculate_cost(
                    meters=meters,
                    start=body.start,
                    end=body.end,
                    resolution=body.resolution,
                )
            except ValueError as e:
                from fastapi import HTTPException

                raise HTTPException(status_code=400, detail=str(e)) from e

            data_rows = _df_to_nested_list(df)

            return BillingResponse(
                metadata=BillingMetadata(
                    start=body.start,
                    end=body.end,
                    resolution=body.resolution,
                ),
                data=[BillingDataPoint(**row) for row in data_rows],
            )

        self.add_api_route(
            "",
            calculate_cost,
            methods=["POST"],
            response_model=BillingResponse,
            summary="Calculate energy cost",
        )
