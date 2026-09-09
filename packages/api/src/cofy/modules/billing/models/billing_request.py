import datetime as dt

import pandas as pd
from energy_cost import Contract, ContractHistory, Meter, MeterType, PowerDirection, TimeseriesFrame
from isodate import Duration
from pydantic import BaseModel, ConfigDict, Field, model_validator

from cofy.modules.timeseries import ISODuration


class DataPoint(BaseModel):
    timestamp: dt.datetime = Field(examples=["2024-01-01T00:00:00+01:00"])
    value: float = Field(examples=[5.5])


class TimeseriesInfo(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    values: list[DataPoint] = Field(
        examples=[
            [
                {"timestamp": "2024-01-01T00:00:00+01:00", "value": 5.5},
                {"timestamp": "2024-01-15T00:00:00+01:00", "value": 7.3},
            ]
        ],
        min_length=1,
    )
    resolution: ISODuration = Field(default_factory=lambda: Duration(months=1), examples=["P1M"])

    def to_timeseries(self, factor) -> TimeseriesFrame:
        data = TimeseriesFrame(
            {
                "timestamp": [dp.timestamp for dp in self.values],
                "value": [dp.value for dp in self.values],
            },
            resolution=self.resolution,
        )
        # convert, eg kWh to MWh for energy_cost, or W to MW
        data["value"] = data["value"] / factor
        # convert iso strings to datetime
        data["timestamp"] = pd.to_datetime(data["timestamp"], format="ISO8601", utc=True)
        return data


class MeterInfo(BaseModel):
    type: MeterType = Field(default=MeterType.SINGLE_RATE, examples=["single_rate"])
    measurements: TimeseriesInfo
    capacity: TimeseriesInfo | None = None

    def to_meter(self, direction: PowerDirection) -> Meter:
        return Meter(
            direction=direction,
            type=self.type,
            measurements=self.measurements.to_timeseries(1000),
            capacity=self.capacity.to_timeseries(1000000) if self.capacity is not None else None,
        )


class BillingRequest(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_schema_extra={
            "examples": [
                {
                    "start": "2024-01-01T00:00:00+01:00",
                    "end": "2024-02-01T00:00:00+01:00",
                    "resolution": "P1M",
                    "consumption": {
                        "type": "single_rate",
                        "measurements": {
                            "values": [
                                {"timestamp": "2024-01-01T00:00:00+01:00", "value": 5.5},
                                {"timestamp": "2024-01-01T00:15:00+01:00", "value": 7.3},
                            ],
                            "resolution": "PT15M",
                        },
                    },
                    "contract": [
                        {
                            "start": "2024-01-01T00:00:00+01:00",
                            "end": "2024-06-30T23:59:59+02:00",
                            "region": "be_flanders",
                            "connection_type": "electricity",
                            "customer_type": "residential",
                            "distributor_key": "fluvius_imewo",
                            "supplier": [
                                {
                                    "start": "2024-01-01T00:00:00+01:00",
                                    "consumption": {"constant_cost": 100},
                                }
                            ],
                        }
                    ],
                }
            ]
        },
    )

    start: dt.datetime | None = None
    end: dt.datetime | None = None
    resolution: ISODuration = Field(default_factory=lambda: Duration(months=1))
    consumption: MeterInfo
    injection: MeterInfo | None = None
    contract: ContractHistory | Contract

    @model_validator(mode="after")
    def end_must_be_after_start(self) -> "BillingRequest":
        if self.start is not None and self.end is not None and self.end <= self.start:
            raise ValueError(f"'end' ({self.end.isoformat()}) must be after 'start' ({self.start.isoformat()}). ")
        return self
