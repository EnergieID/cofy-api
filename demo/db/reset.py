from cofy import CofyDB
from demo.main import DB_CONNECT_ARGS, DB_URL, cofy


def main() -> None:
    db = CofyDB(url=DB_URL, connect_args=DB_CONNECT_ARGS)
    db.bind_api(cofy)
    db.reset()


if __name__ == "__main__":
    main()
