import datetime as dt
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from ..format import TimeseriesFormat, TimeseriesFormatSettings
from ..model import ISODuration, Timeseries

DataType = TypeVar("DataType", bound=BaseModel)
MetadataType = TypeVar("MetadataType", bound=BaseModel)


class DefaultDataType(BaseModel):
    timestamp: dt.datetime
    value: float


class DefaultMetadataType(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    start: dt.datetime | None = None
    end: dt.datetime | None = None
    format: str = "json"
    resolution: ISODuration | None = None
    unit: str | None = None


class ResponseModel(BaseModel, Generic[DataType, MetadataType]):
    metadata: MetadataType
    data: list[DataType]


class JSONFormatSettings(TimeseriesFormatSettings):
    type: str = "json"


class JSONFormat(TimeseriesFormat, Generic[DataType, MetadataType], settings=JSONFormatSettings):
    """Timeseries format for JSON."""

    name = "json"

    # We need to pass the typing info at runtime, otherwise we don't have enough info to create the openapi schema
    # root cause is type erasure, see https://github.com/python/typing/issues/629#issuecomment-1831106590
    def __init__(self, DT: type[DataType] | None = None, MT: type[MetadataType] | None = None):
        super().__init__()
        self.DT = DT or DefaultDataType
        self.MT = MT or DefaultMetadataType
        self.ResponseModel = ResponseModel[self.DT, self.MT]

    def format(self, timeseries: Timeseries) -> ResponseModel:
        return self.ResponseModel(
            metadata=self.MT(**timeseries.metadata),
            data=[self.DT(**row) for row in timeseries.to_arr()],
        )

    @property
    def ReturnType(self) -> type:
        return self.ResponseModel
