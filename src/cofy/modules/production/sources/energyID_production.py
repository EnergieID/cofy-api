import asyncio
import datetime as dt

import polars as pl
import requests
from isodate import strftime
from pydantic import BaseModel

from cofy.modules.timeseries import ISODuration, Timeseries, TimeseriesSource


class EnergyIDDataPoint(BaseModel):
    timestamp: str
    total: float


class EnergyIDValueEntry(BaseModel):
    data: list[EnergyIDDataPoint]
    unit: str = "unknown"


class EnergyIDResponse(BaseModel):
    value: list[EnergyIDValueEntry]


class EnergyIDProduction(TimeseriesSource):
    SUPPORTED_RESOLUTIONS: list[str] = ["PT5M", "PT15M", "PT1H", "P1D", "P7D", "P1M", "P1Y"]

    def __init__(self, api_key: str, record_id: str) -> None:
        super().__init__()
        if not api_key:
            raise ValueError("API key must be provided")
        if not record_id:
            raise ValueError("Record ID must be provided")

        self.headers = {"Authorization": f"apikey {api_key}"}
        self.record_id = record_id

    async def fetch_timeseries(
        self,
        start: dt.datetime,
        end: dt.datetime,
        resolution: ISODuration,
        **kwargs,
    ) -> Timeseries:
        start_date = start.date().isoformat()
        end_date = end.date().isoformat()
        resolution_iso = strftime(resolution, format="P%P")

        if resolution_iso not in self.SUPPORTED_RESOLUTIONS:
            raise ValueError(
                f"Resolution {resolution_iso} is not supported. "
                f"Supported resolutions are: {', '.join(self.SUPPORTED_RESOLUTIONS)}"
            )

        respone = await asyncio.to_thread(
            requests.get,
            f"https://api.energyid.eu/api/v1/records/{self.record_id}/data/energyProduction?start={start_date}&end={end_date}&interval={resolution_iso}",
            headers=self.headers,
        )
        if respone.status_code != 200:
            raise ValueError(f"Failed to fetch data from EnergyID API: {respone.status_code} - {respone.text}")

        parsed = EnergyIDResponse.model_validate(respone.json())
        entry = parsed.value[0]

        data = [
            {
                "timestamp": dt.datetime.fromisoformat(point.timestamp),
                "value": point.total,
            }
            for point in entry.data
        ]
        return Timeseries(
            frame=pl.DataFrame(data),
            metadata={"unit": entry.unit},
        )

    @property
    def supported_resolutions(self) -> list[str]:
        return self.SUPPORTED_RESOLUTIONS
