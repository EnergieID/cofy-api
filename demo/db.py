from importlib import resources

from cofy import CofyDB
from cofy.modules.members import sync_members_from_csv
from demo.main import DB_URL, cofy

MEMBERS_CSV_PATH = str(resources.files("demo.data").joinpath("members_example.csv"))

db = CofyDB(url=DB_URL)
db.bind_api(cofy)


def seed() -> None:
    db.run_migrations()
    sync_members_from_csv(
        db_engine=db.engine,
        file_path=MEMBERS_CSV_PATH,
        id_field="KLANTNUMMER",
        email_field="EMAIL",
        activation_code_field="ACTIVATIECODE",
    )


db.set_seed(seed)

if __name__ == "__main__":
    db.cli()
