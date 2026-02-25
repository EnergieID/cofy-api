from importlib import resources

from src.cofy.db.cofy_db import CofyDB
from src.demo.main import DB_CONNECT_ARGS, DB_URL, cofy
from src.modules.members.tasks.sync_from_csv import sync_members_from_csv

MEMBERS_CSV_PATH = str(resources.files("src.demo.data").joinpath("members_example.csv"))

db = CofyDB(url=DB_URL, connect_args=DB_CONNECT_ARGS)
db.bind_api(cofy)


async def seed() -> None:
    db.run_migrations()
    await sync_members_from_csv(
        db_engine=db.engine,
        file_path=MEMBERS_CSV_PATH,
        id_field="KLANTNUMMER",
        email_field="EMAIL",
        activation_code_field="ACTIVATIECODE",
    )


db.set_seed(seed)

if __name__ == "__main__":
    db.cli()
