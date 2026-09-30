import datetime as dt
import json
from unittest.mock import MagicMock, patch

import pytest

from cofy.integrations.acc import AccForecastSource
from cofy.integrations.acc.acc_forecast import ACC_TIMEOUT
from cofy.modules.timeseries import TimeseriesSource

MODULE = "cofy.integrations.acc.acc_forecast"
BASE_URL = "https://acc.example"
CREDENTIALS = json.dumps({"type": "service_account", "client_email": "test@acc-ops.iam.gserviceaccount.com"})
START = dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC)
END = dt.datetime(2026, 1, 1, 0, 45, tzinfo=dt.UTC)

FIRST_PAGE = {
    "data": [
        {"delivery_start": "2026-01-01T00:00:00Z", "amount_kwh": "1.5"},
        {"delivery_start": "2026-01-01T00:15:00Z", "amount_kwh": "-2.25"},
    ],
    "next": "/v1/connections/541234567890123456/forecasts?cursor=abc",
}
LAST_PAGE = {
    "data": [{"delivery_start": "2026-01-01T00:30:00Z", "amount_kwh": "0"}],
    "next": None,
}


def response(status_code: int, payload: dict | None = None) -> MagicMock:
    mock = MagicMock(status_code=status_code, text="error")
    mock.json.return_value = payload
    return mock


@pytest.fixture
def id_token():
    """Replaces the Google service-account ID token with one that is valid until refreshed."""
    with patch(f"{MODULE}.IDTokenCredentials") as credentials_class:
        credentials = credentials_class.from_service_account_info.return_value
        credentials.valid = False
        credentials.token = "test-token"
        credentials.refresh.side_effect = lambda _request: setattr(credentials, "valid", True)
        yield credentials_class


def test_ean_is_required(id_token):
    with pytest.raises(ValueError):
        AccForecastSource(ean="", credentials=CREDENTIALS)


def test_requests_id_token_for_connection_usage_service(id_token):
    source = AccForecastSource(ean="541234567890123456", credentials=CREDENTIALS)
    id_token.from_service_account_info.assert_not_called()

    assert source.credentials is id_token.from_service_account_info.return_value
    id_token.from_service_account_info.assert_called_once_with(
        json.loads(CREDENTIALS), target_audience="connection-usage"
    )


@pytest.mark.asyncio
async def test_fetches_all_pages(id_token):
    source = AccForecastSource(ean="541234567890123456", credentials=CREDENTIALS, base_url=BASE_URL)

    with patch(f"{MODULE}.requests.get", side_effect=[response(200, FIRST_PAGE), response(200, LAST_PAGE)]) as get:
        result = await source.fetch_timeseries(START, END, dt.timedelta(minutes=15))

    assert result.to_arr() == [
        {"timestamp": START, "value": 1.5},
        {"timestamp": START + dt.timedelta(minutes=15), "value": -2.25},
        {"timestamp": START + dt.timedelta(minutes=30), "value": 0.0},
    ]
    assert result.metadata == {"unit": "kWh"}

    first, second = get.call_args_list
    assert first.args == (f"{BASE_URL}/v1/connections/541234567890123456/forecasts",)
    assert first.kwargs["params"] == {"from_dt": START.isoformat(), "to_dt": END.isoformat()}
    assert first.kwargs["headers"] == {"Authorization": "Bearer test-token"}
    assert first.kwargs["timeout"] == second.kwargs["timeout"] == ACC_TIMEOUT
    assert second.args == (f"{BASE_URL}{FIRST_PAGE['next']}",)
    # the token is refreshed once and reused while valid
    id_token.from_service_account_info.return_value.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_empty_response_gives_empty_timeseries(id_token):
    source = AccForecastSource(ean="541234567890123456", credentials=CREDENTIALS)

    with patch(f"{MODULE}.requests.get", return_value=response(200, {"data": [], "next": None})):
        result = await source.fetch_timeseries(START, END, dt.timedelta(minutes=15))

    assert result.to_arr() == []


@pytest.mark.asyncio
async def test_error_response_raises(id_token):
    source = AccForecastSource(ean="541234567890123456", credentials=CREDENTIALS)

    with (
        patch(f"{MODULE}.requests.get", return_value=response(403)),
        pytest.raises(ValueError, match="403"),
    ):
        await source.fetch_timeseries(START, END, dt.timedelta(minutes=15))


def test_supported_resolutions(id_token):
    source = AccForecastSource(ean="541234567890123456", credentials=CREDENTIALS)

    assert source.supported_resolutions == ["PT15M"]


def test_create_from_settings(id_token):
    source = TimeseriesSource.create(
        {"type": "acc_forecast", "ean": "541234567890123456", "credentials": CREDENTIALS, "base_url": BASE_URL}
    )

    assert isinstance(source, AccForecastSource)
    assert source.ean == "541234567890123456"
    assert source.base_url == BASE_URL
