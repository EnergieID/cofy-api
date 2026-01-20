import narwhals as nw
import datetime as dt
from pydantic import BaseModel

class TariffEntry(BaseModel):
    timestamp: dt.datetime
    value: float

class TariffFrame:
    unit: str
    entries: nw.DataFrame[TariffEntry]

    @nw.narwhalify
    def __init__(self, unit: str, entries: nw.DataFrame[TariffEntry]):
        self.unit = unit
        self.entries = entries