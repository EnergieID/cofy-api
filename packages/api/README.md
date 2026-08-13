# Cofy API

Cofy API is an open-source modular framework for ingesting, standardising, storing, and computing energy-related data.

This package contains the runtime API and module system.

## Install

```sh
pip install "cofy-api[all]"
```

Install only what you need via extras. Example:

```sh
pip install "cofy-api[tariff,members]"
```

## Quick start

Create an app.py file with a minimal Cofy API:

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

The API is available at http://127.0.0.1:8000 with docs at /docs.

## Authentication

Protect the API with bearer-token authentication:

```python
from fastapi import Depends

from cofy import CofyAPI
from cofy.api import token_verifier

app = CofyAPI(dependencies=[Depends(token_verifier({"my-secret-token": {"name": "Admin"}}))])
```

Clients can authenticate via header (Authorization: Bearer my-secret-token) or query parameter (?token=my-secret-token).

## Development

```sh
uv sync --group dev
poe test
poe lint
poe format
poe check
```
