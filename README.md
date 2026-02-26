**Cofy Cloud** is an open-source modular framework for ingesting, standardising, storing, and computing energy-related data, designed to run anywhere from local deployments to cloud environments.

Right now this is very much a work in progress.
With the development of a first proof of concept. This is not ready for production use and the api is likely to change significantly in the near future.

## Setup
### Install
*TODO*
### Configure
*TODO*
### Development
We use [astral](https://docs.astral.sh/) python tooling for our development environment.
We use [poethepoet](https://poethepoet.natn.io) to define some essential tasks.
The demo run task is also available as vscode execution task, making it easy to run and debug the demo application from within vscode.

#### Install/update dependencies:
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

#### Configure environment variables:
Our demo application uses some API keys for external services. You can provide these `.env.local` file in the root of the repository, following the structure of `.env.example`.

#### Set up the database:
The demo application uses a PostgreSQL database. Configure the connection URL via the `DB_URL` environment variable.

Make sure PostgreSQL is running (e.g. via Docker):

```sh
docker run -p 5432:5432 -e POSTGRES_DB=cofy -e POSTGRES_HOST_AUTH_METHOD=trust postgres:16-alpine
```

To create the database tables and seed with example data:

```sh
poe db seed
```

This will run all pending migrations and load the example CSV data into the database.

#### Run development demo application:

```sh
poe demo
```

#### Run background worker:
We use Cofy Worker to run background jobs that perform data ingestion and processing tasks asynchronously.

The background worker uses the same PostgreSQL database as the API (configured via `DB_URL`).

Start the worker:

```sh
poe worker
```

#### Code style checks:
```sh
poe lint    # Check code style
poe format  # Format code
poe check   # Run type checks
```

#### Run tests:
```sh
poe test
```
#### Build & publish
TODO

## Database & Migrations

Cofy uses [Alembic](https://alembic.sqlalchemy.org/) for database migrations. Each module that needs database storage owns its own migration branch, keeping schemas independent and composable.

### Commands

| Command | Description |
|---|---|
| `poe db seed` | Run all migrations and seed the database with example data |
| `poe db migrate` | Run all pending migrations |
| `poe db reset` | Drop all tables and re-run migrations (⚠️ destroys all data) |
| `poe db generate` | Generate a new migration file for a specific module branch |

### Generating a migration

When you change a module's SQLAlchemy model, generate a migration for that module's branch:

```sh
poe db generate "add phone number to member" --head members_core@head --rev-id members_core_0002
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
src/modules/members/migrations/versions/
├── members_core_0001_members_core_initial.py   # branch_labels = ("members_core",)
└── members_core_0002_add_phone_number.py       # extends members_core@head
```

A separate module `foo` would have its own branch `foo_core` with revisions in its own directory:

```
src/modules/foo/migrations/versions/
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
