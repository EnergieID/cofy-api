from fastapi.responses import StreamingResponse

from src.shared.timeseries.formats.csv import CSVFormat


def test_return_type():
    format = CSVFormat()
    assert format.ReturnType == StreamingResponse
