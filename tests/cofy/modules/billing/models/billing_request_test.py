import datetime as dt
from unittest.mock import MagicMock

import pandas as pd
import pytest
from energy_cost import Contract, Meter, MeterType, PowerDirection, Tariff
from pydantic import ValidationError

from cofy.modules.billing.models.billing_request import (
    BillingRequest,
    CustomerType,
    DataPoint,
    MeterInfo,
    make_billing_request_model,
)


class TestDataPoint:
    def test_creates_with_valid_fields(self):
        ts = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        dp = DataPoint(timestamp=ts, value=150.5)
        assert dp.timestamp == ts
        assert dp.value == 150.5


class TestMeterInfo:
    def _dp(self, value: float = 100.0, day: int = 1) -> DataPoint:
        return DataPoint(timestamp=dt.datetime(2024, 1, day, tzinfo=dt.UTC), value=value)

    def _two_dps(self) -> list[DataPoint]:
        return [self._dp(100.0, day=1), self._dp(200.0, day=2)]

    def test_to_meter_has_default_direction_and_type(self):
        info = MeterInfo(data=self._two_dps())
        meter = info.to_meter()
        assert isinstance(meter, Meter)
        assert meter.direction == PowerDirection.CONSUMPTION
        assert meter.type == MeterType.SINGLE_RATE

    def test_to_meter_preserves_explicit_direction_and_type(self):
        info = MeterInfo(direction=PowerDirection.INJECTION, type=MeterType.TOU_PEAK, data=self._two_dps())
        meter = info.to_meter()
        assert meter.direction == PowerDirection.INJECTION
        assert meter.type == MeterType.TOU_PEAK

    def test_to_meter_data_matches_datapoints(self):
        dps = [
            DataPoint(timestamp=dt.datetime(2024, 1, 1, tzinfo=dt.UTC), value=10.0),
            DataPoint(timestamp=dt.datetime(2024, 1, 2, tzinfo=dt.UTC), value=20.0),
        ]
        info = MeterInfo(data=dps)
        meter = info.to_meter()
        assert isinstance(meter.data, pd.DataFrame)
        assert list(meter.data["value"]) == [10.0, 20.0]
        assert list(meter.data["timestamp"]) == [dp.timestamp for dp in dps]

    def test_raises_for_empty_data(self):
        with pytest.raises(ValidationError):
            MeterInfo(data=[])

    def test_raises_for_single_datapoint(self):
        with pytest.raises(ValidationError):
            MeterInfo(data=[self._dp()])


class TestMakeBillingRequestModel:
    @pytest.fixture
    def mock_tariff(self):
        return MagicMock(spec=Tariff)

    def test_returns_subclass_of_billing_request(self, mock_tariff):
        Model = make_billing_request_model(products={"prod1": mock_tariff}, distributors={})
        assert issubclass(Model, BillingRequest)

    def test_contract_field_has_product_and_customer_type(self, mock_tariff):
        Model = make_billing_request_model(products={"prod1": mock_tariff}, distributors={"dist1": mock_tariff})
        schema = Model.model_json_schema()
        contract_props = schema.get("$defs", {})
        # contract fields are reachable via the schema properties
        all_props = str(contract_props)
        assert "product" in all_props
        assert "distributor" in all_props
        assert "customer_type" in all_props

    def _two_dps(self) -> list[DataPoint]:
        return [
            DataPoint(timestamp=dt.datetime(2024, 1, 1, tzinfo=dt.UTC), value=1.0),
            DataPoint(timestamp=dt.datetime(2024, 1, 2, tzinfo=dt.UTC), value=2.0),
        ]

    def _meter(self) -> MeterInfo:
        return MeterInfo(data=self._two_dps())

    def test_accepts_known_product(self, mock_tariff):
        Model = make_billing_request_model(products={"prod1": mock_tariff}, distributors={})
        model = Model(meters=[self._meter()], contract={"product": "prod1"})
        assert model.contract.product == "prod1"

    def test_rejects_unknown_product(self, mock_tariff):
        Model = make_billing_request_model(products={"prod1": mock_tariff}, distributors={})
        with pytest.raises(ValidationError):
            Model(meters=[self._meter()], contract={"product": "unknown"})

    def test_accepts_known_distributor(self, mock_tariff):
        Model = make_billing_request_model(products={}, distributors={"dist1": mock_tariff})
        model = Model(meters=[self._meter()], contract={"distributor": "dist1"})
        assert model.contract.distributor == "dist1"

    def test_rejects_unknown_distributor(self, mock_tariff):
        Model = make_billing_request_model(products={}, distributors={"dist1": mock_tariff})
        with pytest.raises(ValidationError):
            Model(meters=[self._meter()], contract={"distributor": "unknown"})

    def test_rejects_empty_meters_list(self, mock_tariff):
        Model = make_billing_request_model(products={"prod1": mock_tariff}, distributors={})
        with pytest.raises(ValidationError):
            Model(meters=[], contract={})

    def test_json_schema_includes_example(self, mock_tariff):
        Model = make_billing_request_model(products={"prod1": mock_tariff}, distributors={"dist1": mock_tariff})
        schema = Model.model_json_schema()
        assert "examples" in schema


class TestContractInfo:
    @pytest.fixture
    def mock_tariff(self):
        return MagicMock(spec=Tariff)

    @pytest.fixture
    def model(self, mock_tariff):
        Model = make_billing_request_model(
            products={"prod1": mock_tariff},
            distributors={"dist1": mock_tariff},
        )
        dps = [
            DataPoint(timestamp=dt.datetime(2024, 1, 1, tzinfo=dt.UTC), value=1.0),
            DataPoint(timestamp=dt.datetime(2024, 1, 2, tzinfo=dt.UTC), value=2.0),
        ]
        return Model(
            meters=[MeterInfo(data=dps)],
            contract={"customer_type": "residential", "product": "prod1", "distributor": "dist1"},
        )

    def test_to_contract_returns_contract_instance(self, model):
        contract = model.contract.to_contract()
        assert isinstance(contract, Contract)

    def test_to_contract_uses_selected_product(self, model, mock_tariff):
        contract = model.contract.to_contract()
        assert contract.provider is mock_tariff

    def test_to_contract_uses_selected_distributor(self, model, mock_tariff):
        contract = model.contract.to_contract()
        assert contract.distributor is mock_tariff

    def test_to_contract_without_product_sets_none_provider(self, mock_tariff):
        Model = make_billing_request_model(products={"prod1": mock_tariff}, distributors={})
        dps = [
            DataPoint(timestamp=dt.datetime(2024, 1, 1, tzinfo=dt.UTC), value=1.0),
            DataPoint(timestamp=dt.datetime(2024, 1, 2, tzinfo=dt.UTC), value=2.0),
        ]
        model = Model(meters=[MeterInfo(data=dps)], contract={"customer_type": "residential"})
        contract = model.contract.to_contract()
        assert contract.provider is None

    @pytest.mark.parametrize("customer_type", [ct.value for ct in CustomerType])
    def test_to_contract_for_all_customer_types(self, mock_tariff, customer_type):
        Model = make_billing_request_model(products={"prod1": mock_tariff}, distributors={})
        dps = [
            DataPoint(timestamp=dt.datetime(2024, 1, 1, tzinfo=dt.UTC), value=1.0),
            DataPoint(timestamp=dt.datetime(2024, 1, 2, tzinfo=dt.UTC), value=2.0),
        ]
        model = Model(meters=[MeterInfo(data=dps)], contract={"customer_type": customer_type})
        contract = model.contract.to_contract()
        assert isinstance(contract, Contract)
