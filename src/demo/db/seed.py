from importlib import resources

from src.cofy.db.cofy_db import CofyDB
from src.demo.main import DB_CONNECT_ARGS, DB_URL, cofy
from src.demo.members.jobs.load_from_csv import LoadMembersFromCSV

MEMBERS_CSV_PATH = str(resources.files("src.demo.members.jobs").joinpath("example.csv"))


def main() -> None:
    db = CofyDB(url=DB_URL, connect_args=DB_CONNECT_ARGS)
    db.bind_api(cofy)
    db.run_migrations()
    LoadMembersFromCSV(MEMBERS_CSV_PATH, db.engine)()


if __name__ == "__main__":
    main()
