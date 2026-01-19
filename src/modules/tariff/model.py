import narwhals
from pydantic import BaseModel

class TariffEntry(BaseModel):
    timestamp: str
    value: float

class TariffFrame:
    unit: str
    entries: narwhals.DataFrame[TariffEntry]

    def __init__(self, unit: str, entries: narwhals.DataFrame[TariffEntry]):
        self.unit = unit
        self.entries = entries