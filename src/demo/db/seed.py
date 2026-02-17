from importlib import resources

from src.demo.main import cofy
from src.modules.members.jobs.eb_load_from_csv import EBLoadFromCSV

MEMBERS_CSV_PATH = str(
    resources.files("src.modules.members.jobs").joinpath("eb_members_example.csv")
)


def main() -> None:
    if cofy.db is None:
        raise ValueError("Demo seed requires a configured CofyDB instance.")
    cofy.db.run_migrations()
    EBLoadFromCSV(MEMBERS_CSV_PATH, cofy.db.engine)()


if __name__ == "__main__":
    main()
