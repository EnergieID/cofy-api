import datetime as dt
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from energy_cost import CostGroup, Tariff
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cofy.modules.billing import BillingModule


def _make_cost_df(start: dt.datetime) -> pd.DataFrame:
    """Minimal MultiIndex-column DataFrame matching energy_cost output."""
    cols = pd.MultiIndex.from_tuples(
        [
            ("timestamp", "", ""),
            ("taxes", CostGroup.FIXED, "vat"),
            ("total", CostGroup.TOTAL, "total"),
        ]
    )
    return pd.DataFrame([[start, 0.06, 1.0]], columns=cols)


_START = "2024-01-01T00:00:00+00:00"
_END = "2024-02-01T00:00:00+00:00"
_BODY = {
    "start": _START,
    "end": _END,
    "resolution": "P1M",
    "meters": [
        {
            "direction": "consumption",
            "type": "single_rate",
            "data": [{"timestamp": _START, "value": 150.5}],
        }
    ],
    "contract": {
        "customer_type": "residential",
        "product": "product1",
        "distributor": "dist1",
    },
}


@pytest.fixture
def mock_tariff():
    return MagicMock(spec=Tariff)


@pytest.fixture
def module(mock_tariff):
    return BillingModule(
        products={"product1": mock_tariff},
        distributors={"dist1": mock_tariff},
    )


@pytest.fixture
def app(module):
    _app = FastAPI()
    _app.include_router(module)
    return _app


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


# ── Module metadata ───────────────────────────────────────────────────────


def test_billing_module_type(module):
    assert module.type == "billing"


def test_billing_module_default_name(module):
    assert module.name == "default"


def test_billing_module_has_type_description(module):
    assert module.type_description


# ── POST endpoint ─────────────────────────────────────────────────────────


class TestBillingEndpoint:
    def test_post_returns_200_on_success(self, client, module):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        with patch("cofy.modules.billing.models.billing_request.Contract") as MockContract:
            MockContract.return_value.calculate_cost.return_value = _make_cost_df(start)
            response = client.post(module.prefix, json=_BODY)
        assert response.status_code == 200

    def test_post_response_has_metadata_and_data(self, client, module):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        with patch("cofy.modules.billing.models.billing_request.Contract") as MockContract:
            MockContract.return_value.calculate_cost.return_value = _make_cost_df(start)
            response = client.post(module.prefix, json=_BODY)
        body = response.json()
        assert "metadata" in body
        assert "data" in body

    def test_post_response_data_has_one_entry_per_row(self, client, module):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        with patch("cofy.modules.billing.models.billing_request.Contract") as MockContract:
            MockContract.return_value.calculate_cost.return_value = _make_cost_df(start)
            response = client.post(module.prefix, json=_BODY)
        assert len(response.json()["data"]) == 1

    def test_post_response_metadata_reflects_request(self, client, module):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        with patch("cofy.modules.billing.models.billing_request.Contract") as MockContract:
            MockContract.return_value.calculate_cost.return_value = _make_cost_df(start)
            response = client.post(module.prefix, json=_BODY)
        meta = response.json()["metadata"]
        assert meta["start"] is not None
        assert meta["end"] is not None

    def test_post_returns_400_when_calculate_raises_value_error(self, client, module):
        with patch("cofy.modules.billing.models.billing_request.Contract") as MockContract:
            MockContract.return_value.calculate_cost.side_effect = ValueError("bad input")
            response = client.post(module.prefix, json=_BODY)
        assert response.status_code == 400
        assert "bad input" in response.json()["detail"]

    def test_post_returns_422_for_unknown_product(self, client, module):
        body = {**_BODY, "contract": {"customer_type": "residential", "product": "unknown"}}
        response = client.post(module.prefix, json=body)
        assert response.status_code == 422

    def test_post_returns_422_for_unknown_distributor(self, client, module):
        body = {**_BODY, "contract": {"customer_type": "residential", "distributor": "unknown"}}
        response = client.post(module.prefix, json=body)
        assert response.status_code == 422

    def test_post_returns_422_for_missing_meters(self, client, module):
        body = {k: v for k, v in _BODY.items() if k != "meters"}
        response = client.post(module.prefix, json=body)
        assert response.status_code == 422

    def test_post_works_without_start_and_end(self, client, module):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        body = {k: v for k, v in _BODY.items() if k not in ("start", "end")}
        with patch("cofy.modules.billing.models.billing_request.Contract") as MockContract:
            MockContract.return_value.calculate_cost.return_value = _make_cost_df(start)
            response = client.post(module.prefix, json=body)
        assert response.status_code == 200

    def test_post_passes_correct_args_to_calculate_cost(self, client, module):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        with patch("cofy.modules.billing.models.billing_request.Contract") as MockContract:
            mock_contract = MockContract.return_value
            mock_contract.calculate_cost.return_value = _make_cost_df(start)
            client.post(module.prefix, json=_BODY)
        call_kwargs = mock_contract.calculate_cost.call_args.kwargs
        assert "meters" in call_kwargs
        assert len(call_kwargs["meters"]) == 1
