from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.modules.members.models.db_member import DBMember
from src.modules.members.sources.db_source import MembersDbSource


def _setup_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    DBMember.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            DBMember(
                id="1",
                email="member@example.com",
                activation_code="secret-code",
            )
        )
        session.add(
            DBMember(
                id="2",
                email="another@example.com",
                activation_code="another-secret",
            )
        )
        session.commit()

    return engine


def test_members_db_source_list_and_verify():
    source = MembersDbSource(_setup_engine())

    members = source.list(email="member@example.com")
    assert len(members) == 1
    assert members[0].id == "1"

    member = source.verify("secret-code")
    assert member is not None
    assert member.id == "1"

    assert source.verify("invalid") is None


def test_members_db_source_exposes_migration_metadata():
    source = MembersDbSource(_setup_engine())

    assert source.target_metadata is DBMember.metadata
    assert len(source.migration_locations) == 1
