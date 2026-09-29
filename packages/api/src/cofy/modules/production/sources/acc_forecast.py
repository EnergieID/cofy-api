import asyncio
import datetime as dt
import json
from functools import cached_property
from typing import Literal
from urllib.parse import urljoin

import polars as pl
import requests
from google.auth.transport.requests import Request
from google.oauth2.service_account import IDTokenCredentials
from pydantic import BaseModel

from cofy.api import Secret
from cofy.modules.timeseries import ISODuration, Timeseries, TimeseriesSource, TimeseriesSourceSettings

ACC_BASE_URL = "https://connection-usage-service-prd-730943142752.europe-west1.run.app"
ACC_TARGET_AUDIENCE = "connection-usage"
# seconds; without one a hanging ACC blocks the request, and the cache lock held for it, indefinitely
ACC_TIMEOUT = 30


class AccForecastSettings(TimeseriesSourceSettings):
    type: Literal["acc_forecast"] = "acc_forecast"
    ean: str
    credentials: Secret
    base_url: str = ACC_BASE_URL


class AccForecast(BaseModel):
    delivery_start: dt.datetime
    amount_kwh: float


class AccForecastPage(BaseModel):
    data: list[AccForecast]
    next: str | None = None


class AccForecastSource(TimeseriesSource, settings=AccForecastSettings):
    def __init__(self, ean: str, credentials: str, base_url: str = ACC_BASE_URL) -> None:
        """Net forecasted consumption (positive) or production (negative) in kWh per quarter-hour for one EAN, from ACC's Connection Usage Service.

        Args:
            ean: EAN18 code of the connection.
            credentials: Google service-account credentials JSON provided by ACC.
            base_url: Base URL of the Connection Usage Service.
        """
        super().__init__()
        if not ean:
            raise ValueError("EAN must be provided")

        self.ean = ean
        self.base_url = base_url.rstrip("/")
        self._service_account = credentials

    @cached_property
    def credentials(self) -> IDTokenCredentials:
        # built on first use, so a misconfigured source fails its requests rather than app startup
        return IDTokenCredentials.from_service_account_info(
            json.loads(self._service_account), target_audience=ACC_TARGET_AUDIENCE
        )

    def _get(self, url: str, params: dict | None = None) -> AccForecastPage:
        if not self.credentials.valid:
            self.credentials.refresh(Request())

        response = requests.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {self.credentials.token}"},
            timeout=ACC_TIMEOUT,
        )
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch forecasts from ACC: {response.status_code} - {response.text}")
        return AccForecastPage.model_validate(response.json())

    def _fetch_all(self, start: dt.datetime, end: dt.datetime) -> list[AccForecast]:
        page = self._get(
            f"{self.base_url}/v1/connections/{self.ean}/forecasts",
            {"from_dt": start.isoformat(), "to_dt": end.isoformat()},
        )
        forecasts = list(page.data)
        while page.next:
            page = self._get(urljoin(self.base_url, page.next))
            forecasts.extend(page.data)
        return forecasts

    async def fetch_timeseries(
        self,
        start: dt.datetime,
        end: dt.datetime,
        resolution: ISODuration,
        **kwargs,
    ) -> Timeseries:
        forecasts = await asyncio.to_thread(self._fetch_all, start, end)
        frame = pl.DataFrame(
            {
                "timestamp": [f.delivery_start for f in forecasts],
                "value": [f.amount_kwh for f in forecasts],
            },
            schema={"timestamp": pl.Datetime(time_zone="UTC"), "value": pl.Float64},
        )
        return Timeseries(frame=frame, metadata={"unit": "kWh"})

    @property
    def supported_resolutions(self) -> list[str]:
        return ["PT15M"]
