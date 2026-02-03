from fastapi import Response

from src.shared.timeseries.format import TimeseriesFormat
from src.shared.timeseries.model import Timeseries


class CSVFormat(TimeseriesFormat):
    """Timeseries format for CSV."""

    name = "csv"

    def format(self, timeseries: Timeseries) -> Response:
        return Response(
            content=timeseries.to_csv(),
            media_type="text/csv",
            headers={"metadata": timeseries.metadata},
        )

    @property
    def ReturnType(self) -> type:
        return Response
