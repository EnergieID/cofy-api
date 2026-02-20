import argparse

from src.cofy.db.cofy_db import CofyDB
from src.demo.main import DB_CONNECT_ARGS, DB_URL, cofy


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a new Alembic migration for a module branch.")
    parser.add_argument("message", help="Migration description")
    parser.add_argument(
        "--head",
        required=True,
        help="Branch head to extend, e.g. 'members_core@head'",
    )
    parser.add_argument(
        "--rev-id",
        default=None,
        help="Custom revision ID (optional, Alembic generates one if omitted)",
    )
    parser.add_argument(
        "--no-autogenerate",
        action="store_true",
        help="Create an empty migration instead of autogenerating from model changes",
    )
    args = parser.parse_args()

    db = CofyDB(url=DB_URL, connect_args=DB_CONNECT_ARGS)
    db.bind_api(cofy)
    db.generate_migration(
        message=args.message,
        head=args.head,
        rev_id=args.rev_id,
        autogenerate=not args.no_autogenerate,
    )


if __name__ == "__main__":
    main()
