import datetime as dt
from unittest.mock import MagicMock, patch

import pandas as pd
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

_DST_BODY = {
    "contract": {
        "customer_type": "residential",
        "distributor": "fluvius_antwerpen",
        "product": "dynamic",
    },
    # end is 2024-03-30T22:04:00Z — BEFORE start (2024-03-30T23:00:00Z) in UTC
    "end": "2024-03-31T00:04:00+02:00",
    "meters": [
        {
            "data": [
                {"timestamp": "2024-03-31T01:45:00+01:00", "value": 150.5},
                {"timestamp": "2024-03-31T03:00:00+02:00", "value": 75.3},
            ],
            "direction": "consumption",
            "type": "single_rate",
        }
    ],
    "resolution": "P1M",
    "start": "2024-03-31T00:00:00+01:00",
}


# ── Module metadata ───────────────────────────────────────────────────────


class TestBillingModuleMetadata:
    def setup_method(self):
        mock_tariff = MagicMock(spec=Tariff)
        self.module = BillingModule(
            products={"product1": mock_tariff},
            distributors={"dist1": mock_tariff},
        )

    def test_type(self):
        assert self.module.type == "billing"

    def test_default_name(self):
        assert self.module.name == "default"

    def test_has_type_description(self):
        assert self.module.type_description


# ── POST endpoint ─────────────────────────────────────────────────────────


class TestBillingEndpoint:
    def setup_method(self):
        mock_tariff = MagicMock(spec=Tariff)
        self.module = BillingModule(
            products={"product1": mock_tariff},
            distributors={"dist1": mock_tariff},
        )
        app = FastAPI()
        app.include_router(self.module)
        self.client = TestClient(app, raise_server_exceptions=False)

    def test_post_returns_200_on_success(self):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        with patch("cofy.modules.billing.models.billing_request.Contract") as MockContract:
            MockContract.return_value.calculate_cost.return_value = _make_cost_df(start)
            response = self.client.post(self.module.prefix, json=_BODY)
        assert response.status_code == 200

    def test_post_response_has_metadata_and_data(self):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        with patch("cofy.modules.billing.models.billing_request.Contract") as MockContract:
            MockContract.return_value.calculate_cost.return_value = _make_cost_df(start)
            response = self.client.post(self.module.prefix, json=_BODY)
        body = response.json()
        assert "metadata" in body
        assert "data" in body

    def test_post_response_data_has_one_entry_per_row(self):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        with patch("cofy.modules.billing.models.billing_request.Contract") as MockContract:
            MockContract.return_value.calculate_cost.return_value = _make_cost_df(start)
            response = self.client.post(self.module.prefix, json=_BODY)
        assert len(response.json()["data"]) == 1

    def test_post_response_metadata_reflects_request(self):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        with patch("cofy.modules.billing.models.billing_request.Contract") as MockContract:
            MockContract.return_value.calculate_cost.return_value = _make_cost_df(start)
            response = self.client.post(self.module.prefix, json=_BODY)
        meta = response.json()["metadata"]
        assert meta["start"] is not None
        assert meta["end"] is not None

    def test_post_returns_400_when_calculate_raises_value_error(self):
        with patch("cofy.modules.billing.models.billing_request.Contract") as MockContract:
            MockContract.return_value.calculate_cost.side_effect = ValueError("bad input")
            response = self.client.post(self.module.prefix, json=_BODY)
        assert response.status_code == 400
        assert "bad input" in response.json()["detail"]

    def test_post_returns_422_for_unknown_product(self):
        body = {**_BODY, "contract": {"customer_type": "residential", "product": "unknown"}}
        response = self.client.post(self.module.prefix, json=body)
        assert response.status_code == 422

    def test_post_returns_422_for_unknown_distributor(self):
        body = {**_BODY, "contract": {"customer_type": "residential", "distributor": "unknown"}}
        response = self.client.post(self.module.prefix, json=body)
        assert response.status_code == 422

    def test_post_returns_422_for_missing_meters(self):
        body = {k: v for k, v in _BODY.items() if k != "meters"}
        response = self.client.post(self.module.prefix, json=body)
        assert response.status_code == 422

    def test_post_works_without_start_and_end(self):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        body = {k: v for k, v in _BODY.items() if k not in ("start", "end")}
        with patch("cofy.modules.billing.models.billing_request.Contract") as MockContract:
            MockContract.return_value.calculate_cost.return_value = _make_cost_df(start)
            response = self.client.post(self.module.prefix, json=body)
        assert response.status_code == 200

    def test_post_passes_correct_args_to_calculate_cost(self):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        with patch("cofy.modules.billing.models.billing_request.Contract") as MockContract:
            mock_contract = MockContract.return_value
            mock_contract.calculate_cost.return_value = _make_cost_df(start)
            self.client.post(self.module.prefix, json=_BODY)
        call_kwargs = mock_contract.calculate_cost.call_args.kwargs
        assert "meters" in call_kwargs
        assert len(call_kwargs["meters"]) == 1


# ── DST boundary regression ───────────────────────────────────────────────


class TestDSTBoundary:
    def setup_method(self):
        mock_tariff = MagicMock(spec=Tariff)
        self.module = BillingModule(
            products={"dynamic": mock_tariff},
            distributors={"fluvius_antwerpen": mock_tariff},
        )
        app = FastAPI()
        app.include_router(self.module)
        self.client = TestClient(app, raise_server_exceptions=False)

    def test_end_before_start_after_dst_returns_422(self):
        """start=00:00+01:00 and end=00:04+02:00 on DST change day: end is before start in UTC."""
        response = self.client.post(self.module.prefix, json=_DST_BODY)
        assert response.status_code == 422

    def test_end_before_start_after_dst_does_not_return_500(self):
        """The DST edge case must not cause an unhandled 500 error."""
        response = self.client.post(self.module.prefix, json=_DST_BODY)
        assert response.status_code != 500
