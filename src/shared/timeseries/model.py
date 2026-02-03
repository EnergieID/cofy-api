import datetime as dt

import narwhals as nw
from pydantic import BaseModel


class DefaultDataType(BaseModel):
    timestamp: dt.datetime
    value: float


class DefaultMetadataType(BaseModel):
    start: dt.datetime | None = None
    end: dt.datetime | None = None
    format: str = "unknown"
    resolution: str | None = None


class Timeseries[
    DataType: BaseModel = DefaultDataType,
    MetadataType: BaseModel = DefaultMetadataType,
]:
    frame: nw.DataFrame
    metadata: MetadataType

    @nw.narwhalify
    def __init__(self, frame: nw.DataFrame, metadata: dict | None = None):
        self.frame = frame
        self.metadata = MetadataType(**(metadata or {}))

    def to_csv(self) -> str:
        return self.frame.write_csv()

    def to_arr(self) -> list[DataType]:
        return [DataType(**row) for row in self.frame.iter_rows(named=True)]
