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
from cofy import CofyAPI
from cofy.modules.tariff import TariffModule

app = CofyAPI()
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

from cofy import CofyAPI
from cofy.api import token_verifier

app = CofyAPI(
    dependencies=[Depends(token_verifier({"my-secret-token": {"name": "Admin"}}))]
)
```

Clients authenticate via header (`Authorization: Bearer my-secret-token`) or query parameter (`?token=my-secret-token`).

#### Full example

The [demo/](demo/) directory contains a complete working application that ties everything together.

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

### Run development demo application:

Our demo application uses some API keys for external services. You can provide these `.env.local` file in the root of the repository, following the structure of `.env.example`.

```sh
poe demo
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
