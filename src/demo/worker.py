"""
SAQ worker configuration for the Demo community.

Defines which jobs are available, their cron schedules,
and shared resources (database engine, etc.).

Run with:
    poe worker
    # or directly:
    saq src.demo.worker.settings
"""

from os import environ

from sqlalchemy import create_engine

from src.cofy.jobs.worker import CofyWorker
from src.modules.members.jobs.sync_from_csv import sync_members_from_csv

# --- Configuration (from environment) ---
REDIS_URL = environ.get("REDIS_URL", "redis://localhost:6379")
DB_URL = environ.get("DB_URL", "sqlite:///./demo.db")
CSV_PATH = environ.get("MEMBERS_CSV_PATH", "src/demo/members/jobs/example.csv")


# --- Worker setup ---
worker = CofyWorker(url=REDIS_URL)


# --- Lifecycle hooks: set up shared resources available to all jobs via ctx ---
@worker.on_startup
async def startup(ctx: dict) -> None:
    ctx["db_engine"] = create_engine(DB_URL)


@worker.on_shutdown
async def shutdown(ctx: dict) -> None:
    ctx["db_engine"].dispose()


# --- Register job functions available in this community ---
worker.register(sync_members_from_csv)

# --- Cron schedules for this community ---
# Sync members from CSV every night at 2 AM
worker.schedule(sync_members_from_csv, cron="0 2 * * *")


# --- SAQ entry point ---
settings = worker.settings
