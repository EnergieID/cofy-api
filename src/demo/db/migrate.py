from src.demo.main import cofy


def main() -> None:
    cofy.db.run_migrations()


if __name__ == "__main__":
    main()
