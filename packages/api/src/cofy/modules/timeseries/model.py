from datetime import timedelta
from typing import Annotated

import narwhals as nw
from isodate import Duration, parse_duration, strftime
from pydantic import BeforeValidator, Field, PlainSerializer

ISODuration = Annotated[
    timedelta | Duration,
    BeforeValidator(lambda v: parse_duration(v) if isinstance(v, str) else v),
    PlainSerializer(lambda v: strftime(v, "P%P"), return_type=str),
    Field(
        description="ISO-8601 duration",
        examples=["PT15M", "P1D"],
    ),
]


def _parse_timedelta(value: object) -> object:
    parsed = parse_duration(value) if isinstance(value, str) else value
    if isinstance(parsed, Duration):
        raise ValueError("Only durations without years or months are supported, as they have no fixed length")
    return parsed


ISOTimedelta = Annotated[
    timedelta,
    BeforeValidator(_parse_timedelta),
    PlainSerializer(lambda v: strftime(v, "P%P"), return_type=str),
    Field(
        description="ISO-8601 duration without years or months",
        examples=["PT15M", "P1D"],
    ),
]


class Timeseries:
    frame: nw.DataFrame
    metadata: dict

    @nw.narwhalify
    def __init__(self, frame: nw.DataFrame, metadata: dict | None = None):
        self.frame = frame
        self.metadata = metadata or {}

    def to_csv(self) -> str:
        return self.frame.write_csv()

    def to_arr(self) -> list[dict]:
        return [row for row in self.frame.iter_rows(named=True)]
