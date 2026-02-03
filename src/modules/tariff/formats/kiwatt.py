from datetime import UTC, datetime

from pydantic import BaseModel

from src.modules.tariff.model import TariffMetadata
from src.shared.timeseries.format import TimeseriesFormat
from src.shared.timeseries.model import DefaultDataType, Timeseries


def to_utc_timestring(dt: datetime | str) -> str:
    dt_obj = datetime.fromisoformat(dt) if isinstance(dt, str) else dt
    return dt_obj.astimezone(UTC).replace(microsecond=0).isoformat()


class PriceRecordModel(BaseModel):
    startUTC: str
    value: float


class ResponseModel(BaseModel):
    generatedAtUTC: str
    periodStartUTC: str
    periodEndUTC: str
    source: str
    unit: str
    resolution: str
    prices: list[PriceRecordModel]


class KiwattFormat(TimeseriesFormat):
    """Timeseries format for Kiwatt."""

    name = "kiwatt"

    def format(self, timeseries: Timeseries[DefaultDataType, TariffMetadata]):
        return ResponseModel(
            generatedAtUTC=to_utc_timestring(datetime.now(UTC)),
            periodStartUTC=to_utc_timestring(timeseries.metadata.start),
            periodEndUTC=to_utc_timestring(timeseries.metadata.end),
            source="Energy-ID-DeltaWind",
            unit=timeseries.metadata.unit,
            resolution=timeseries.metadata.resolution,
            prices=[
                PriceRecordModel(
                    startUTC=to_utc_timestring(row.timestamp), value=row.value
                )
                for row in timeseries.to_arr()
            ],
        )

    @property
    def ReturnType(self) -> type:
        return ResponseModel
