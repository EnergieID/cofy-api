import datetime as dt

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from src.demo.members.models import DemoMember, DemoProduct
from src.demo.members.source import DemoMembersDbSource
from src.modules.members.module import MembersModule


def _setup_demo_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        member = DemoMember(
            id="1",
            email="member@example.com",
            activation_code="secret-code",
        )
        product = DemoProduct(
            id=123,
            member_id="1",
            name="Energy Product",
            ean=123,
            start_date=dt.date(2026, 1, 1),
        )
        session.add(member)
        session.add(product)
        session.commit()

    return engine


def test_demo_source_filters_members_by_ean():
    source = DemoMembersDbSource(_setup_demo_engine())

    members = source.list(ean=123)
    assert len(members) == 1
    assert members[0].products[0].ean == 123


def test_demo_verify_endpoint_returns_demo_member_payload():
    app = FastAPI()
    module = MembersModule(
        settings={
            "source": DemoMembersDbSource(_setup_demo_engine()),
            "name": "energybar",
        }
    )
    app.include_router(module)
    client = TestClient(app)

    response = client.post(
        module.prefix + "/verify", json={"activation_code": "secret-code"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "1"
    assert payload["products"][0]["ean"] == 123
