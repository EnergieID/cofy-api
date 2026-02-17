from importlib import resources
from pathlib import Path

DB_PATH = Path(str(resources.files("src.demo.db").joinpath("database.db")))


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()


if __name__ == "__main__":
    main()
