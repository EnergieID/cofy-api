"""
SAQ worker configuration for the Demo community.

Defines which jobs are available, their cron schedules,
and shared resources (database engine, etc.).

Run with:
    poe worker
    # or directly:
    saq src.demo.worker.settings
"""

from importlib import resources
from os import environ

from sqlalchemy import create_engine

from src.cofy.worker import CofyWorker
from src.modules.members.tasks.sync_from_csv import sync_members_from_csv

# --- Configuration (from environment) ---
REDIS_URL = environ.get("REDIS_URL", "redis://localhost:6379")
DB_URL = environ.get("DB_URL", "sqlite:///./demo.db")
CSV_PATH = str(resources.files("src.demo.data").joinpath("members_example.csv"))


# --- Worker setup ---
worker = CofyWorker(url=REDIS_URL)


# --- Lifecycle hooks: set up shared resources available to all jobs via ctx ---
@worker.on_startup
async def startup(ctx: dict) -> None:
    ctx["db_engine"] = create_engine(DB_URL)


# --- Register and schedule jobs for this community ---
# db_engine comes from ctx (set in startup); CSV field mapping is fixed for this community.
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
