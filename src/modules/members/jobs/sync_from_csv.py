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


async def sync_members_from_csv(ctx: dict, *, file_path: str) -> dict:
    """Load or update members from a CSV file into the database.

    The CSV must have columns: KLANTNUMMER, EMAIL, ACTIVATIECODE.

    Args:
        ctx: SAQ job context — must contain 'db_engine' (SQLAlchemy Engine).
        file_path: Absolute path to the CSV file.

    Returns:
        Summary dict with counts: {"created": int, "updated": int}
    """
    engine = ctx["db_engine"]
    created = 0
    updated = 0

    with open(file_path) as f, Session(engine) as session:
        reader = csv.DictReader(f)
        for row in reader:
            member_id = row["KLANTNUMMER"]
            email = row["EMAIL"]
            activation_code = row["ACTIVATIECODE"]

            member = session.get(DBMember, member_id)
            if member is None:
                member = DBMember(id=member_id, email=email, activation_code=activation_code)
                created += 1
            else:
                member.email = email
                member.activation_code = activation_code
                updated += 1
            session.add(member)
        session.commit()

    return {"created": created, "updated": updated}
