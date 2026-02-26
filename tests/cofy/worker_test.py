import pytest

from src.cofy import worker as worker_module


class DummyQueue:
    def __init__(self, url: str, **kwargs):
        self.url = url
        self.kwargs = kwargs

    @staticmethod
    def from_url(url: str, **kwargs):
        return DummyQueue(url, **kwargs)


class DummyCronJob:
    def __init__(self, function, cron: str, kwargs: dict, **extra_kwargs):
        self.function = function
        self.cron = cron
        self.kwargs = kwargs
        self.extra_kwargs = extra_kwargs


@pytest.fixture
def worker_module_with_doubles(monkeypatch):
    monkeypatch.setattr(worker_module, "Queue", DummyQueue)
    monkeypatch.setattr(worker_module, "CronJob", DummyCronJob)
    return worker_module


def test_create_queue_forwards_url_and_kwargs(worker_module_with_doubles):
    queue = worker_module_with_doubles.create_queue("postgresql://example/cofy", name="jobs")

    assert isinstance(queue, DummyQueue)
    assert queue.url == "postgresql://example/cofy"
    assert queue.kwargs == {"name": "jobs"}


@pytest.mark.asyncio
async def test_to_task_merges_kwargs_with_expected_precedence():
    def sync_job(db_engine: str, file_path: str):
        return f"{db_engine}:{file_path}"

    task = worker_module.to_task(sync_job, db_engine="fixed_engine", file_path="fixed.csv")

    result = await task(
        {"db_engine": "ctx_engine", "queue": object()},
        file_path="enqueue.csv",
        ignored="not_in_signature",
    )

    assert result == "ctx_engine:enqueue.csv"


@pytest.mark.asyncio
async def test_to_task_supports_async_functions_with_var_kwargs():
    async def async_job(required: str, **kwargs):
        return required, kwargs

    task = worker_module.to_task(async_job, fixed="yes", required="fixed")

    required, kwargs = await task({"from_ctx": 1}, required="enqueue", from_enqueue=2)

    assert required == "enqueue"
    assert kwargs == {"fixed": "yes", "from_ctx": 1, "from_enqueue": 2}


def test_schedule_registers_function_and_cron_job(worker_module_with_doubles):
    worker = worker_module_with_doubles.CofyWorker(url="postgresql://example/cofy", db=3)

    async def sample_job(x: int = 0):
        return x

    task = worker.schedule(
        sample_job,
        cron="0 2 * * *",
        function_kwargs={"x": 42},
        timezone="UTC",
    )

    settings = worker.settings
    cron_job = settings["cron_jobs"][0]

    assert isinstance(settings["queue"], DummyQueue)
    assert settings["queue"].kwargs == {"db": 3}
    assert settings["functions"] == [task]
    assert isinstance(cron_job, DummyCronJob)
    assert cron_job.function is task
    assert cron_job.cron == "0 2 * * *"
    assert cron_job.kwargs == {"x": 42}
    assert cron_job.extra_kwargs == {"timezone": "UTC"}


def test_registering_the_same_function_multiple_times_does_not_duplicate(worker_module_with_doubles):
    worker = worker_module_with_doubles.CofyWorker("postgresql://example/cofy")

    def sample_job():
        pass

    task1 = worker.register(sample_job)
    task2 = worker.register(sample_job)

    assert task1 is task2
    assert len(worker.settings["functions"]) == 1
    assert worker.settings["functions"][0] is task1
    assert worker.settings["functions"][0] is task2


@pytest.mark.asyncio
async def test_registering_the_same_function_twice_with_different_kwargs_keeps_original_kwargs(
    worker_module_with_doubles,
):
    worker = worker_module_with_doubles.CofyWorker("postgresql://example/cofy")

    def sample_job(x: int = 0):
        return x

    task1 = worker.register(sample_job, x=1)
    task2 = worker.register(sample_job, x=2)

    assert task1 is task2
    assert len(worker.settings["functions"]) == 1
    assert worker.settings["functions"][0] is task1
    assert worker.settings["functions"][0] is task2
    assert await task1({}) == 1


@pytest.mark.asyncio
async def test_settings_startup_and_shutdown_hooks_run_in_registration_order(worker_module_with_doubles):
    worker = worker_module_with_doubles.CofyWorker("postgresql://example/cofy")
    events = []

    @worker.on_startup
    async def startup_one(ctx: dict):
        events.append("startup_one")
        ctx["ready"] = True

    @worker.on_startup
    async def startup_two(ctx: dict):
        events.append("startup_two")

    @worker.on_shutdown
    async def shutdown_one(ctx: dict):
        events.append(f"shutdown_one:{ctx['ready']}")

    settings = worker.settings
    ctx = {}

    await settings["startup"](ctx)
    await settings["shutdown"](ctx)

    assert events == ["startup_one", "startup_two", "shutdown_one:True"]


def test_settings_without_lifecycle_hooks_only_contains_core_keys(worker_module_with_doubles):
    worker = worker_module_with_doubles.CofyWorker("postgresql://example/cofy")

    settings = worker.settings

    assert set(settings.keys()) == {"queue", "functions", "cron_jobs"}
