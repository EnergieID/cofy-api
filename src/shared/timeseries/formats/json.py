import datetime as dt

from pydantic import BaseModel, ConfigDict

from src.shared.timeseries.format import TimeseriesFormat
from src.shared.timeseries.model import ISODuration, Timeseries


class DefaultDataType(BaseModel):
    timestamp: dt.datetime
    value: float


class DefaultMetadataType(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    start: dt.datetime | None = None
    end: dt.datetime | None = None
    format: str = "json"
    resolution: ISODuration | None = None


class ResponseModel[
    DataType: BaseModel = DefaultDataType,
    MetadataType: BaseModel = DefaultMetadataType,
](BaseModel):
    metadata: MetadataType
    data: list[DataType]


class JSONFormat[
    DataType: BaseModel = DefaultDataType,
    MetadataType: BaseModel = DefaultMetadataType,
](TimeseriesFormat):
    """Timeseries format for JSON."""

    name = "json"

    # We need to pass the typing info at runtime, otherwise we don't have enough info to create the openapi schema
    # root cause is type erasure, see https://github.com/python/typing/issues/629#issuecomment-1831106590
    def __init__(
        self, DT: type[DataType] | None = None, MT: type[MetadataType] | None = None
    ):
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
