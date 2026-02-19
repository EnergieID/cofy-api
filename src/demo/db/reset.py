from src.demo.main import cofy


def main() -> None:
    if cofy.db is None:
        raise ValueError("Demo reset requires a configured CofyDB instance.")
    cofy.db.reset()


if __name__ == "__main__":
    main()
