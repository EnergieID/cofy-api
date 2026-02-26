import narwhals as nw


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
