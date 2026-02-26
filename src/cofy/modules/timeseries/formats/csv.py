from fastapi.responses import StreamingResponse

from ..format import TimeseriesFormat
from ..model import Timeseries
from .json import DefaultMetadataType


class CSVFormat(TimeseriesFormat):
    """Timeseries format for CSV."""

    name = "csv"

    def format(self, timeseries: Timeseries) -> StreamingResponse:
        return StreamingResponse(
            content=timeseries.to_csv(),
            media_type="text/csv",
            headers={"x-metadata": DefaultMetadataType(**timeseries.metadata).model_dump_json()},
        )

    @property
    def ReturnType(self) -> type:
        return StreamingResponse

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
                "headers": {
                    "x-metadata": {
                        "description": "Metadata for the timeseries as a JSON-encoded string",
                        "schema": {
                            "type": "string",
                            "contentMediaType": "application/json",
                            "contentSchema": DefaultMetadataType.model_json_schema(),
                        },
                    }
                },
            }
        }

    @property
    def response_class(self) -> type[StreamingResponse]:
        """Return the response class for this format."""
        return StreamingResponse
