from src.demo.main import cofy


def main() -> None:
    if cofy.db is None:
        raise ValueError("Demo migrate requires a configured CofyDB instance.")
    cofy.db.run_migrations()


if __name__ == "__main__":
    main()
