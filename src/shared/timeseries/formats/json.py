from typing import TypeVar

from pydantic import BaseModel

from src.shared.timeseries.format import TimeseriesFormat
from src.shared.timeseries.model import Timeseries


class ResponseModel[DataType: BaseModel, MetadataType: BaseModel](BaseModel):
    metadata: MetadataType
    data: list[DataType]


class JSONFormat[DataType: BaseModel, MetadataType: BaseModel](TimeseriesFormat):
    """Timeseries format for JSON."""

    name = "json"

    # We need to pass the typing info at runtime, otherwise we don't have enough info to create the openapi schema
    # root cause is type erasure, see https://github.com/python/typing/issues/629#issuecomment-1831106590
    def __init__(self, dt: type[DataType] | TypeVar, mt: type[MetadataType] | TypeVar):
        super().__init__()
        self.response_model = ResponseModel[dt, mt]

    def format(
        self, timeseries: Timeseries[DataType, MetadataType]
    ) -> ResponseModel[DataType, MetadataType]:
        return self.response_model(
            metadata=timeseries.metadata, data=timeseries.to_arr()
        )

    @property
    def ReturnType(self) -> type:
        return self.response_model
