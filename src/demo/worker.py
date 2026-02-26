from importlib import resources
from os import environ

from sqlalchemy import create_engine

from src.cofy.worker import CofyWorker
from src.modules.members.tasks.sync_from_csv import sync_members_from_csv

DB_URL = environ.get("DB_URL", "")
assert DB_URL, "DB_URL environment variable must be set to connect to the database"
# SAQ needs a plain postgresql:// URL (without the SQLAlchemy +psycopg driver spec)
QUEUE_URL = DB_URL.replace("+psycopg", "", 1)
CSV_PATH = str(resources.files("src.demo.data").joinpath("members_example.csv"))

worker = CofyWorker(url=QUEUE_URL)


@worker.on_startup
async def startup(ctx: dict) -> None:
    ctx["db_engine"] = create_engine(DB_URL)


@worker.on_shutdown
async def shutdown(ctx: dict) -> None:
    ctx["db_engine"].dispose()


worker.schedule(
    sync_members_from_csv,
    cron="0 2 * * *",
    function_kwargs={
        "file_path": CSV_PATH,
        "id_field": "KLANTNUMMER",
        "email_field": "EMAIL",
        "activation_code_field": "ACTIVATIECODE",
    },
)


# --- SAQ entry point ---
settings = worker.settings
