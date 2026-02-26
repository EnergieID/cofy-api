from importlib import resources
from os import environ

from sqlalchemy import create_engine

from cofy.modules.members.tasks.sync_from_csv import sync_members_from_csv
from cofy.worker import CofyWorker

REDIS_URL = environ.get("REDIS_URL", "redis://localhost:6379")
DB_URL = environ.get("DB_URL", "sqlite:///./demo.db")
CSV_PATH = str(resources.files("demo.data").joinpath("members_example.csv"))

worker = CofyWorker(url=REDIS_URL)


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
