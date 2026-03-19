from importlib import resources
from os import environ

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from cofy.modules.members import sync_members_from_csv
from cofy.worker import CofyWorker

DB_URL = environ.get("DB_URL", "")
assert DB_URL, "DB_URL environment variable must be set to connect to the database"


def _to_saq_queue_url(db_url: str) -> str:
    url = make_url(db_url)
    # SAQ expects a plain backend URL (e.g. postgresql://) without SQLAlchemy driver hints.
    return url.set(drivername=url.get_backend_name()).render_as_string(hide_password=False)


QUEUE_URL = _to_saq_queue_url(DB_URL)
CSV_PATH = str(resources.files("demo.data").joinpath("members_example.csv"))

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
