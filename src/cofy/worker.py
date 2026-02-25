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

    worker = CofyWorker(url="redis://localhost:6379")
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

import asyncio
import functools
import inspect
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


def to_task(function: Callable, **fixed_kwargs: Any) -> JobFunction:
    """Wrap a plain function into a SAQ-compatible task.

    The wrapped function does NOT need to know about SAQ's `ctx` dict.
    It simply declares the arguments it needs::

        async def sync_members(db_engine, file_path: str) -> dict: ...

    Arguments are resolved in this priority order (last wins):
        1. fixed_kwargs — bound at registration time via ``to_task(fn, file_path="/data/x.csv")``
        2. ctx values — set by the worker's on_startup hooks (e.g. ``db_engine``)
        3. enqueue kwargs — passed at ``queue.enqueue("sync_members", file_path="/other.csv")``

    Only arguments that match the function's signature are passed through,
    so SAQ internals in ctx (``queue``, ``job``) don't leak in.

    Works with both sync and async functions. Sync functions are
    automatically run in a thread via ``asyncio.to_thread``.
    """
    sig = inspect.signature(function)
    params = sig.parameters
    accepts_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
    is_async = inspect.iscoroutinefunction(function)

    @functools.wraps(function)
    async def task(ctx: dict, **kwargs: Any) -> Any:
        merged = {**fixed_kwargs, **ctx, **kwargs}

        call_kwargs = merged if accepts_var_keyword else {k: v for k, v in merged.items() if k in params}

        if is_async:
            return await function(**call_kwargs)
        return await asyncio.to_thread(function, **call_kwargs)

    return task


class CofyWorker:
    """Builds SAQ worker settings from registered job functions and cron schedules.

    The worker collects job functions and cron schedules, then exposes them as a `settings` dict for the SAQ CLI.

    It also provides lifecycle hooks (on_startup / on_shutdown) for setting up shared resources like database engines
    """

    def __init__(self, url: str = "redis://localhost:6379", **queue_kwargs: Any):
        self.queue = Queue.from_url(url, **queue_kwargs)
        self._functions: list[JobFunction] = []
        self._cron_jobs: list[CronJob] = []
        self._startup_hooks: list[JobFunction] = []
        self._shutdown_hooks: list[JobFunction] = []

    def register(self, func: Callable, **fixed_kwargs: Any) -> JobFunction:
        """Register a job function so it can be enqueued and processed by this worker.

        Registered functions become available for ``queue.enqueue("function_name", ...)``.
        """
        task = to_task(func, **fixed_kwargs)
        if task not in self._functions:
            self._functions.append(task)
        return task

    def schedule(
        self,
        func: Callable,
        cron: str,
        function_kwargs: dict | None = None,
        **kwargs: Any,
    ) -> JobFunction:
        """Schedule a function to run on a cron expression."""
        task = self.register(func)
        self._cron_jobs.append(
            CronJob(task, cron=cron, kwargs=function_kwargs or {}, **kwargs),
        )
        return task

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
