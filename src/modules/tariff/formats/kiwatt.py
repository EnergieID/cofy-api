from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, ConfigDict

from src.shared.timeseries.format import TimeseriesFormat
from src.shared.timeseries.model import ISODuration, Timeseries


def to_utc_timestring(dt: datetime | str) -> str:
    dt_obj = datetime.fromisoformat(dt) if isinstance(dt, str) else dt
    return dt_obj.astimezone(UTC).replace(microsecond=0).isoformat()


class PriceRecordModel(BaseModel):
    startUTC: str = "2025-08-28T22:00:00"
    value: float = 82.10


class ResponseModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    generatedAtUTC: str = "2025-08-28T11:15:00"
    periodStartUTC: str = "2025-08-28T22:00:00"
    periodEndUTC: str = "2025-08-29T22:00:00"
    source: str = "Cofy-API-Demo"
    unit: str = "EUR/MWh"
    resolution: ISODuration = timedelta(minutes=15)
    prices: list[PriceRecordModel]


class KiwattFormat(TimeseriesFormat):
    """Timeseries format for Kiwatt."""

    name = "kiwatt"

    def __init__(self, source: str = "Cofy-API-Demo"):
        super().__init__()
        self.source = source

    def format(self, timeseries: Timeseries):
        return ResponseModel(
            generatedAtUTC=to_utc_timestring(datetime.now(UTC)),
            periodStartUTC=to_utc_timestring(timeseries.metadata["start"]),
            periodEndUTC=to_utc_timestring(timeseries.metadata["end"]),
            source=self.source,
            unit=timeseries.metadata["unit"],
            resolution=timeseries.metadata["resolution"],
            prices=[
                PriceRecordModel(
                    startUTC=to_utc_timestring(row["timestamp"]), value=row["value"]
                )
                for row in timeseries.to_arr()
            ],
        )

    @property
    def ReturnType(self) -> type:
        return ResponseModel
