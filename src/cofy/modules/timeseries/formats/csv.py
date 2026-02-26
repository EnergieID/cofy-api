from fastapi.responses import StreamingResponse

from cofy.modules.timeseries.format import TimeseriesFormat
from cofy.modules.timeseries.formats.json import DefaultMetadataType
from cofy.modules.timeseries.model import Timeseries


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
