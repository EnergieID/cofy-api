"""
Provides CofyWorker — a thin scaffolding layer over SAQ for background job processing.

Each community (deployment) creates its own worker with the jobs and cron
schedules it needs. Modules provide reusable job functions; the community
decides which ones to activate and how to schedule them.

Architecture:
    ┌─────────────┐     ┌─────────┐     ┌──────────────┐
    │ FastAPI API │────▶│  Redis  │◀────│  SAQ Worker  │
    │  (enqueue)  │     │  Queue  │     │  (process)   │
    └─────────────┘     └─────────┘     └──────────────┘

Both the API and the worker connect to the same Redis queue.
The API enqueues jobs; the worker processes them.

Example — community worker (e.g. src/demo/worker.py):

    from src.cofy.jobs.worker import CofyWorker

    worker = CofyWorker(redis_url="redis://localhost:6379")
    worker.register(my_job_function)
    worker.schedule(my_job_function, cron="0 2 * * *")
    settings = worker.settings  # SAQ entry point: saq src.demo.worker.settings

Example — enqueue from a FastAPI endpoint:

    from src.cofy.jobs.worker import create_queue

    queue = create_queue("redis://localhost:6379")

    @app.post("/upload")
    async def upload(file: UploadFile):
        await queue.enqueue("process_upload", file_id="...")
"""

from collections.abc import Callable, Coroutine
from typing import Any

from saq import CronJob, Queue

type JobFunction = Callable[..., Coroutine[Any, Any, Any]]


def create_queue(url: str = "redis://localhost:6379", **kwargs: Any) -> Queue:
    """Create a SAQ queue for enqueuing jobs (e.g. from the API process).

    Use this in the API process when you only need to enqueue jobs,
    not process them. Points to the same Redis as the worker.
    """
    return Queue.from_url(url, **kwargs)


class CofyWorker:
    """Builds SAQ worker settings from registered job functions and cron schedules.

    The worker collects job functions (from modules or community-specific code)
    and cron schedules, then exposes them as a `settings` dict for the SAQ CLI.

    It also provides lifecycle hooks (on_startup / on_shutdown) for setting up
    shared resources like database engines that jobs can access via `ctx`.
    """

    def __init__(self, url: str = "redis://localhost:6379", **queue_kwargs: Any):
        self.queue = Queue.from_url(url, **queue_kwargs)
        self._functions: list[JobFunction] = []
        self._cron_jobs: list[CronJob] = []
        self._startup_hooks: list[JobFunction] = []
        self._shutdown_hooks: list[JobFunction] = []

    def register(self, func: JobFunction) -> JobFunction:
        """Register a job function so it can be enqueued and processed by this worker.

        Registered functions become available for `queue.enqueue("function_name", ...)`.
        """
        if func not in self._functions:
            self._functions.append(func)
        return func

    def schedule(self, func: JobFunction, cron: str, **kwargs: Any) -> None:
        """Schedule a function to run on a cron expression.

        The function is automatically registered if not already.

        Args:
            func: The async job function to schedule.
            cron: Cron expression, e.g. "0 2 * * *" for daily at 2 AM.
            **kwargs: Additional SAQ CronJob options (timeout, retries, etc.)
        """
        self.register(func)
        self._cron_jobs.append(CronJob(func, cron=cron, **kwargs))

    def on_startup(self, func: JobFunction) -> JobFunction:
        """Register a hook that runs when the worker starts.

        Use this to set up shared resources (DB engines, HTTP clients, etc.)
        that jobs can access through `ctx`.
        """
        self._startup_hooks.append(func)
        return func

    def on_shutdown(self, func: JobFunction) -> JobFunction:
        """Register a hook that runs when the worker stops. Use for cleanup."""
        self._shutdown_hooks.append(func)
        return func

    @property
    def settings(self) -> dict[str, Any]:
        """SAQ worker settings dict.

        Export this as a module-level `settings` variable for the SAQ CLI:

            settings = worker.settings
            # Run with: saq src.demo.worker.settings
        """
        result: dict[str, Any] = {
            "queue": self.queue,
            "functions": self._functions,
            "cron_jobs": self._cron_jobs,
        }

        if self._startup_hooks:
            hooks = list(self._startup_hooks)

            async def startup(ctx: dict) -> None:
                for hook in hooks:
                    await hook(ctx)

            result["startup"] = startup

        if self._shutdown_hooks:
            hooks = list(self._shutdown_hooks)

            async def shutdown(ctx: dict) -> None:
                for hook in hooks:
                    await hook(ctx)

            result["shutdown"] = shutdown

        return result
