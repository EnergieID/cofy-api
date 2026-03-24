import datetime as dt

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cofy.modules.directive import DirectiveFormat, DirectiveModule, DirectiveSource

from ..timeseries.dummy_source import DummyTimeseriesSource


def test_directivemodule_type_property():
    module = DirectiveModule(source=DirectiveSource(DummyTimeseriesSource(), boundries=(5, 15, 25, 35)))
    assert module.type == "directive"


def test_formats_default():
    module = DirectiveModule(source=DirectiveSource(DummyTimeseriesSource(), boundries=(5, 15, 25, 35)))
    assert len(module.formats) == 1
    assert isinstance(module.formats[0], DirectiveFormat)


def test_api_endpoint_returns_directives():
    start = dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC)
    end = dt.datetime(2026, 1, 1, 3, 0, tzinfo=dt.UTC)
    module = DirectiveModule(
        source=DirectiveSource(DummyTimeseriesSource(), boundries=(5, 15, 25, 35)),
    )

    app = FastAPI()
    app.include_router(module)
    client = TestClient(app)

    response = client.get(
        module.prefix,
        params={
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["format"] == "json"
    assert payload["metadata"]["resolution"] == "PT1H"
    assert [entry["value"] for entry in payload["data"]] == ["--", "-", "0"]
