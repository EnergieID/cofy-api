# Cofy API

Cofy API is an open-source modular framework for ingesting, standardising, storing, and computing energy-related data.

This package contains the runtime API and module system.

## Install

```sh
pip install "cofy-api[all]"
```

Cofy is modular — install only what you need via [extras](https://packaging.python.org/en/latest/specifications/dependency-specifiers/#extras).
Example — install with only the tarrif and members modules:

```sh
pip install "cofy-api[tariff,members]"
```

## Quick start

Create an app.py file with a minimal Cofy API:

```python
from cofy.api import CofyAPI
from cofy.modules.tariff import TariffModule

app = CofyAPI()
app.register_module(TariffModule(api_key="YOUR_ENTSOE_KEY", name="entsoe"))
```

Run it:

```sh
fastapi dev app.py
```

The API is now available at `http://127.0.0.1:8000` with interactive docs at `/docs`.

## Authentication

Protect the API with bearer-token authentication:

```python
from cofy.api import CofyAPI, TokenAuth, TokenInfo

app = CofyAPI(auth=TokenAuth({"my-secret-token": TokenInfo(name="Admin")}))
```

Clients authenticate via header (`Authorization: Bearer my-secret-token`) or query parameter (`?token=my-secret-token`).


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

### Tests and linting

```sh
uv sync --group dev
poe test
poe lint
poe format
poe check
```
