from fastapi.responses import FileResponse

from src.shared.timeseries.format import TimeseriesFormat
from src.shared.timeseries.model import Timeseries


class CSVFormat(TimeseriesFormat):
    """Timeseries format for CSV."""

    name = "csv"

    def format(self, timeseries: Timeseries) -> FileResponse:
        return FileResponse(
            content=timeseries.to_csv(),
            media_type="text/csv",
            headers={"metadata": timeseries.metadata},
        )

    @property
    def ReturnType(self) -> type:
        return FileResponse

    @property
    def responses(self) -> dict:
        return {
            200: {
                "content": {
                    "text/csv": {
                        "schema": {"type": "string", "format": "csv"},
                        "example": "timestamp,value\n2023-01-01T00:00:00Z,123.45\n",
                    }
                },
                "description": "Timeseries data in CSV format",
            }
        }

    @property
    def response_class(self) -> type:
        """Return the response class for this format."""
        return FileResponse
