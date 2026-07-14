import datetime as dt
from unittest.mock import patch

import pandas as pd
from energy_cost import CostGroup
from energy_cost.contract import ContractHistory as EnergyContractHistory
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cofy.api.module import Module
from cofy.modules.billing import BillingModule


def _make_cost_df(start: dt.datetime) -> pd.DataFrame:
    """Minimal MultiIndex-column DataFrame matching energy_cost output."""
    cols = pd.MultiIndex.from_tuples(
        [
            ("timestamp", "", ""),
            ("taxes", CostGroup.FIXED, "vat"),
            ("total", "total", "total"),
        ]
    )
    return pd.DataFrame([[start, 0.06, 1.0]], columns=cols)


_START = "2024-01-01T00:00:00+00:00"
_END = "2024-02-01T00:00:00+00:00"
_METER: dict = {
    "type": "single_rate",
    "measurements": {
        "values": [
            {"timestamp": _START, "value": 150.5},
            {"timestamp": "2024-01-15T00:00:00+00:00", "value": 75.3},
        ],
        "resolution": "P15D",
    },
}
# Contract as ContractHistory (list of versions)
_BODY = {
    "start": _START,
    "end": _END,
    "resolution": "P1M",
    "consumption": _METER,
    "contract": [{"start": _START, "supplier": [{"consumption": {"energy": {"constant_cost": 100}}, "start": _START}]}],
}

_DST_BODY = {
    "contract": [{"start": "2024-03-31T00:00:00+01:00"}],
    # end is 2024-03-30T22:04:00Z — BEFORE start (2024-03-30T23:00:00Z) in UTC
    "end": "2024-03-31T00:04:00+02:00",
    "consumption": {
        "measurements": {
            "values": [
                {"timestamp": "2024-03-31T01:45:00+01:00", "value": 150.5},
                {"timestamp": "2024-03-31T03:00:00+02:00", "value": 75.3},
            ],
            "resolution": "PT15M",
        },
        "type": "single_rate",
    },
    "resolution": "P1M",
    "start": "2024-03-31T00:00:00+01:00",
}


# ── Module metadata ───────────────────────────────────────────────────────


class TestBillingModuleMetadata:
    def setup_method(self):
        self.module = BillingModule()

    def test_type(self):
        assert self.module.type == "billing"

    def test_default_name(self):
        assert self.module.name == "default"

    def test_has_type_description(self):
        assert self.module.type_description


# ── POST endpoint ─────────────────────────────────────────────────────────


class TestBillingEndpoint:
    def setup_method(self):
        self.module = BillingModule()
        app = FastAPI()
        app.include_router(self.module)
        self.client = TestClient(app, raise_server_exceptions=False)

    def test_post_returns_200_on_success(self):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        with patch.object(EnergyContractHistory, "apply", return_value=_make_cost_df(start)):
            response = self.client.post(self.module.prefix, json=_BODY)
        assert response.status_code == 200

    def test_post_response_has_metadata_and_data(self):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        with patch.object(EnergyContractHistory, "apply", return_value=_make_cost_df(start)):
            response = self.client.post(self.module.prefix, json=_BODY)
        body = response.json()
        assert "metadata" in body
        assert "data" in body

    def test_post_response_data_has_one_entry_per_row(self):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        with patch.object(EnergyContractHistory, "apply", return_value=_make_cost_df(start)):
            response = self.client.post(self.module.prefix, json=_BODY)
        assert len(response.json()["data"]) == 1

    def test_post_response_metadata_reflects_request(self):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        with patch.object(EnergyContractHistory, "apply", return_value=_make_cost_df(start)):
            response = self.client.post(self.module.prefix, json=_BODY)
        meta = response.json()["metadata"]
        assert meta["start"] is not None
        assert meta["end"] is not None

    def test_post_returns_400_when_apply_raises_value_error(self):
        with patch.object(EnergyContractHistory, "apply", side_effect=ValueError("bad input")):
            response = self.client.post(self.module.prefix, json=_BODY)
        assert response.status_code == 400
        assert "bad input" in response.json()["detail"]

    def test_post_returns_400_when_apply_returns_none(self):
        with patch.object(EnergyContractHistory, "apply", return_value=None):
            response = self.client.post(self.module.prefix, json=_BODY)
        assert response.status_code == 400
        assert "No cost data" in response.json()["detail"]

    def test_post_returns_422_for_missing_consumption(self):
        body = {k: v for k, v in _BODY.items() if k != "consumption"}
        response = self.client.post(self.module.prefix, json=body)
        assert response.status_code == 422

    def test_post_returns_422_for_empty_meter_data(self):
        body = {**_BODY, "consumption": {"type": "single_rate", "measurements": {"values": [], "resolution": "PT15M"}}}
        response = self.client.post(self.module.prefix, json=body)
        assert response.status_code == 422

    def test_post_returns_200_for_single_datapoint(self):
        body = {
            **_BODY,
            "consumption": {
                "type": "single_rate",
                "measurements": {"values": [{"timestamp": _START, "value": 100.0}], "resolution": "PT15M"},
            },
        }
        response = self.client.post(self.module.prefix, json=body)
        assert response.status_code == 200

    def test_post_works_without_start_and_end(self):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        body = {k: v for k, v in _BODY.items() if k not in ("start", "end")}
        with patch.object(EnergyContractHistory, "apply", return_value=_make_cost_df(start)):
            response = self.client.post(self.module.prefix, json=body)
        assert response.status_code == 200


# ── DST boundary regression ───────────────────────────────────────────────


class TestDSTBoundary:
    def setup_method(self):
        self.module = BillingModule()
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


# -------------------------------------------


def test_create_from_settings():
    module = Module.create({"type": "billing"})

    assert isinstance(module, BillingModule)
