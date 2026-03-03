from fastapi.responses import StreamingResponse

from cofy.modules.timeseries import CSVFormat


def test_return_type():
    format = CSVFormat()
    assert format.ReturnType == StreamingResponse
