**Cofy Cloud** is an open-source modular framework for ingesting, standardising, storing, and computing energy-related data, designed to run anywhere from local deployments to cloud environments.

Right now this is very much a work in progress.
With the development of a first proof of concept. This is not ready for production use and the api is likely to change significantly in the near future.

## Setup

### Install

```sh
pip install "cofy-api[all]"
```

Cofy is modular — install only what you need via [extras](https://packaging.python.org/en/latest/specifications/dependency-specifiers/#extras).
Example — install with only the tarrif and members modules:

```sh
pip install "cofy-api[tariff,members]"
```

### Configure

#### Quick start

Create an `app.py` with a minimal Cofy API:

```python
from cofy import CofyApi
from cofy.modules.tariff import TariffModule

app = CofyApi()
app.register_module(TariffModule(api_key="YOUR_ENTSOE_KEY", name="entsoe"))
```

Run it:

```sh
fastapi dev app.py
```

The API is now available at `http://127.0.0.1:8000` with interactive docs at `/docs`.

#### Authentication

Protect the API with bearer-token authentication:

```python
from fastapi import Depends

from cofy import CofyApi
from cofy.api import token_verifier

app = CofyApi(
    dependencies=[Depends(token_verifier({"my-secret-token": {"name": "Admin"}}))]
)
```

Clients authenticate via header (`Authorization: Bearer my-secret-token`) or query parameter (`?token=my-secret-token`).

#### Database

Modules that need persistence (like `members`) require a database. Any SQLAlchemy-supported database works — just change the URL.

```python
from cofy import CofyApi, CofyDB
from cofy.modules.members import MembersDbSource, MembersModule
from sqlalchemy import create_engine

engine = create_engine("sqlite:///./app.db")

app = CofyApi()
app.register_module(MembersModule(source=MembersDbSource(engine), name="members"))

```

##### Migrations
To setup your database schema, and update it as your models evolve, we offer `CofyDB` — a thin wrapper around [Alembic](https://alembic.sqlalchemy.org/en/latest/). See [Database & Migrations](#database--migrations) for details.

Create a `db.py`:

```python
from cofy import CofyDB
from .main import app

db = CofyDB(url="sqlite:///./app.db")
db.bind_api(app)

if __name__ == "__main__":
    db.cli()
```

Run it:

```sh
python db.py migrate # Run all pending migrations
python db.py reset   # Drop all tables and re-run migrations (⚠️ destroys all data)
``` 

##### Seeding data
If you have seed data (e.g. example CSVs), you can create a seed function and run it via the CLI:

```python
def seed(engine):
    # load example data into the database
    with engine.connect() as conn:
        conn.execute("INSERT INTO members (id, email) VALUES (1, 'alice@example.com')")

db.set_seed(seed)
```

Then run:

```sh
python db.py seed
```

#### Background worker

The worker runs async jobs (data ingestion, scheduled syncs) via Redis and [SAQ](https://github.com/tobymao/saq). Create a `worker.py`:

```python
from cofy import CofyWorker
from cofy.modules.members import sync_members_from_csv
from sqlalchemy import create_engine

worker = CofyWorker(url="redis://localhost:6379")

@worker.on_startup
async def startup(ctx: dict) -> None:
    ctx["db_engine"] = create_engine("sqlite:///./app.db")

@worker.on_shutdown
async def shutdown(ctx: dict) -> None:
    ctx["db_engine"].dispose()

worker.schedule(
    sync_members_from_csv,
    cron="0 2 * * *",
    function_kwargs={
        "file_path": "/data/members.csv",
        "id_field": "ID",
        "email_field": "EMAIL",
        "activation_code_field": "CODE",
    },
)

settings = worker.settings  # SAQ entry point
```

Run it:

```sh
saq worker.settings
```

#### Full example

The [demo/](demo/) directory contains a complete working application that ties everything together — API with auth, database, multiple modules, and a background worker.

## Development
We use [astral](https://docs.astral.sh/) python tooling for our development environment.
We use [poethepoet](https://poethepoet.natn.io) to define some essential tasks.
The demo run task is also available as vscode execution task, making it easy to run and debug the demo application from within vscode.

### Install/update dependencies:
First install [uv](https://docs.astral.sh/uv/) if you don't have it yet.

Then install/update dependencies:
```sh
uv sync
```

Install [poethepoet](https://poethepoet.natn.io) and [pre-commit](https://pre-commit.com/)
```sh
uv tool install poethepoet
uv tool install pre-commit
```

Activate [pre-commit](https://pre-commit.com/) hooks that enforce code style on every commit:
```sh
pre-commit install
```

### Configure environment variables:
Our demo application uses some API keys for external services. You can provide these `.env.local` file in the root of the repository, following the structure of `.env.example`.

### Set up the database:
The demo application uses a SQLite database. A different database can be configured via the environment variables.
To create the database and seed it with example data:

```sh
poe db seed
```

This will run all pending migrations and load the example CSV data into the database.

### Run development demo application:

```sh
poe demo
```

### Run background worker:
We use Cofy Worker to run background jobs that perform data ingestion and processing tasks asynchronously.

The background worker requires a Redis instance to run. You can configure the Redis URL via the environment variables.
The simplest way to run Redis locally is via Docker:

```sh
docker run -p 6379:6379 redis
```

Then start the worker:

```sh
poe worker
```

### Code style checks:
```sh
poe lint    # Check code style
poe format  # Format code
poe check   # Run type checks
```

### Run tests:
```sh
poe test
```
### Build & publish
We use a github action to create a new tag, github release and publish to pypi. Trigger the action manually from the actions tab, and provide the new version number as input.

## Database & Migrations

Cofy uses [Alembic](https://alembic.sqlalchemy.org/) for database migrations. Each module that needs database storage owns its own migration branch, keeping schemas independent and composable.

### Commands
`CofyDB` provides a simple CLI for managing your database and migrations. It supports the following commands:

| Command | Description |
|---|---|
| `seed` | Seed the database with example data |
| `migrate` | Run all pending migrations |
| `reset` | Drop all tables and re-run migrations (⚠️ destroys all data) |
| `generate` | Generate a new migration file for a specific module branch |

### Generating a migration

When you change a module's SQLAlchemy model, generate a migration for that module's branch:

```sh
python db.py generate "add phone number to member" --head members_core@head --rev-id members_core_0002
```

| Argument | Required | Description |
|---|---|---|
| `message` (positional) | ✅ | Short description of the change |
| `--head` | ✅ | Branch to extend, e.g. `members_core@head` |
| `--rev-id` | ❌ | Custom revision ID (Alembic generates one if omitted) |
| `--no-autogenerate` | ❌ | Create an empty migration instead of diffing model changes |

The generated file will be placed in the module's own `migrations/versions/` directory automatically.

### How branches work

Each module declares its own Alembic branch label in its initial migration. This allows multiple modules to coexist in the same database without interfering with each other.

For example, the members module uses branch `members_core`:

```
src/cofy/modules/members/migrations/versions/
├── members_core_0001_members_core_initial.py   # branch_labels = ("members_core",)
└── members_core_0002_add_phone_number.py       # extends members_core@head
```

A separate module `foo` would have its own branch `foo_core` with revisions in its own directory:

```
src/cofy/modules/foo/migrations/versions/
├── foo_core_0001_initial.py                    # branch_labels = ("foo_core",)
└── foo_core_0002_add_index.py                  # extends foo_core@head
```

When `poe db migrate` runs, Alembic upgrades all branches to their latest head — both `members_core` and `foo_core` are applied independently.

### Extending a module's schema

If you build a custom implementation that extends an existing module's schema, you can create a new branch that depends on a specific revision:

```python
revision = "members_custom_0001"
down_revision = None
branch_labels = ("members_custom",)
depends_on = "members_core_0001"  # ensures the base schema exists first
```

This guarantees the base tables are created before your extension runs, while keeping both migration chains independent.
