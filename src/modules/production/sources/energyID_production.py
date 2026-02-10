import asyncio
import datetime as dt

import polars as pl
import requests
from isodate import Duration, strftime

from src.shared.timeseries.model import Timeseries
from src.shared.timeseries.source import TimeseriesSource


class EnergyIDProduction(TimeseriesSource):
    def __init__(self, api_key: str, record_id: str) -> None:
        super().__init__()
        assert api_key, "API key must be provided"
        assert record_id, "Record ID must be provided"

        self.headers = {"Authorization": f"apikey {api_key}"}
        response = requests.get(
            "https://api.energyid.eu/api/v1/members/me", headers=self.headers
        )
        if response.status_code != 200:
            raise ValueError("Invalid API key provided for EnergyIDProduction source.")
        self.record_id = record_id

    async def fetch_timeseries(
        self,
        start: dt.datetime,
        end: dt.datetime,
        resolution: dt.timedelta | Duration,
        **kwargs,
    ) -> Timeseries:
        start_date = start.date().isoformat()
        end_date = end.date().isoformat()
        resolution_iso = strftime(resolution, format="P%P")
        respone = await asyncio.to_thread(
            requests.get,
            f"https://api.energyid.eu/api/v1/records/{self.record_id}/data/energyProduction?start={start_date}&end={end_date}&interval={resolution_iso}",
            headers=self.headers,
        )
        if respone.status_code != 200:
            raise ValueError(
                f"Failed to fetch data from EnergyID API: {respone.status_code} - {respone.text}"
            )
        json = respone.json()

        assert "value" in json, (
            "Response from EnergyID API does not contain 'value' field"
        )
        assert isinstance(json["value"], list), "Expected 'value' field to be a list"
        assert len(json["value"]) > 0, "No data points returned from EnergyID API"
        assert "data" in json["value"][0], (
            "Data points in 'value' list do not contain 'data' field"
        )

        data = [
            {
                "timestamp": dt.datetime.fromisoformat(point["timestamp"]),
                "value": point["total"],
            }
            for point in json["value"][0]["data"]
        ]
        return Timeseries(
            frame=pl.DataFrame(data),
            metadata={"unit": json["value"][0].get("unit", "unknown")},
        )
