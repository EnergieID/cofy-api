import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.modules.members.models.db_member import DBMember
from src.modules.members.tasks.sync_from_csv import sync_members_from_csv


@pytest.fixture
def engine():
    db_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    DBMember.metadata.create_all(db_engine)
    return db_engine


@pytest.mark.asyncio
async def test_sync_members_from_csv_inserts_new_members(engine, tmp_path):
    csv_file = tmp_path / "members.csv"
    csv_file.write_text("ID,EMAIL,CODE\n1,a@example.com,code-a\n2,b@example.com,code-b\n")

    await sync_members_from_csv(
        db_engine=engine,
        file_path=str(csv_file),
        id_field="ID",
        email_field="EMAIL",
        activation_code_field="CODE",
    )

    with Session(engine) as session:
        members = session.scalars(select(DBMember).order_by(DBMember.id)).all()

    assert len(members) == 2
    assert members[0].id == "1"
    assert members[0].email == "a@example.com"
    assert members[0].activation_code == "code-a"
    assert members[1].id == "2"
    assert members[1].email == "b@example.com"
    assert members[1].activation_code == "code-b"


@pytest.mark.asyncio
async def test_sync_members_from_csv_updates_existing_members(engine, tmp_path):
    with Session(engine) as session:
        session.add(DBMember(id="1", email="old@example.com", activation_code="old-code"))
        session.commit()

    csv_file = tmp_path / "members.csv"
    csv_file.write_text("ID,EMAIL,CODE\n1,new@example.com,new-code\n")

    await sync_members_from_csv(
        db_engine=engine,
        file_path=str(csv_file),
        id_field="ID",
        email_field="EMAIL",
        activation_code_field="CODE",
    )

    with Session(engine) as session:
        member = session.get(DBMember, "1")

    assert member is not None
    assert member.email == "new@example.com"
    assert member.activation_code == "new-code"


@pytest.mark.asyncio
async def test_sync_members_from_csv_allows_missing_optional_fields(engine, tmp_path):
    csv_file = tmp_path / "members.csv"
    csv_file.write_text("ID\nonly-id\n")

    await sync_members_from_csv(
        db_engine=engine,
        file_path=str(csv_file),
        id_field="ID",
    )

    with Session(engine) as session:
        member = session.get(DBMember, "only-id")

    assert member is not None
    assert member.email is None
    assert member.activation_code is None
