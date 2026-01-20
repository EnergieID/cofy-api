import narwhals as nw
from pydantic import BaseModel

class TariffEntry(BaseModel):
    timestamp: str
    value: float

class TariffFrame:
    unit: str
    entries: nw.DataFrame[TariffEntry]

    @nw.narwhalify
    def __init__(self, unit: str, entries: nw.DataFrame[TariffEntry]):
        self.unit = unit
        self.entries = entries