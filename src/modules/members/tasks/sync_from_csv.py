"""
Reusable SAQ job: sync members from a CSV file into the database.

Expects `db_engine` (SQLAlchemy Engine) to be available in the SAQ context,
typically set up via the worker's on_startup hook.

Usage — register in a community worker:

    from src.modules.members.jobs.sync_from_csv import sync_members_from_csv

    worker.register(sync_members_from_csv)
    worker.schedule(sync_members_from_csv, cron="0 2 * * *")

Usage — enqueue on demand from an API endpoint:

    await queue.enqueue("sync_members_from_csv", file_path="/data/members.csv")
"""

import csv

from sqlalchemy.orm import Session

from src.modules.members.models.db_member import DBMember


def sync_members_from_csv(
    db_engine, file_path: str, id_field: str, email_field: str | None = None, activation_code_field: str | None = None
) -> None:
    """Load or update members from a CSV file into the database."""
    with open(file_path) as f, Session(db_engine) as session:
        reader = csv.DictReader(f)
        for row in reader:
            member_id = row[id_field]
            email = row[email_field] if email_field else None
            activation_code = row[activation_code_field] if activation_code_field else None

            member = session.get(DBMember, member_id)
            if member is None:
                member = DBMember(id=member_id, email=email, activation_code=activation_code)
            else:
                member.email = email
                member.activation_code = activation_code
            session.add(member)
        session.commit()
