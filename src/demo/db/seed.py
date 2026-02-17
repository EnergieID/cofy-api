from importlib import resources

from src.demo.main import cofy
from src.demo.members.jobs.load_from_csv import LoadMembersFromCSV

MEMBERS_CSV_PATH = str(
    resources.files("src.demo.members.jobs").joinpath("members_example.csv")
)


def main() -> None:
    if cofy.db is None:
        raise ValueError("Demo seed requires a configured CofyDB instance.")
    cofy.db.run_migrations()
    LoadMembersFromCSV(MEMBERS_CSV_PATH, cofy.db.engine)()


if __name__ == "__main__":
    main()
