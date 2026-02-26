from importlib import resources

from cofy import CofyDB
from cofy.modules.members import sync_members_from_csv
from demo.main import DB_CONNECT_ARGS, DB_URL, cofy

MEMBERS_CSV_PATH = str(resources.files("demo.data").joinpath("members_example.csv"))


def main() -> None:
    db = CofyDB(url=DB_URL, connect_args=DB_CONNECT_ARGS)
    db.bind_api(cofy)
    db.run_migrations()
    sync_members_from_csv(
        db_engine=db.engine,
        file_path=MEMBERS_CSV_PATH,
        id_field="KLANTNUMMER",
        email_field="EMAIL",
        activation_code_field="ACTIVATIECODE",
    )


if __name__ == "__main__":
    main()
