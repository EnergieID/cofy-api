# Cofy API

Cofy API is an open-source modular framework for ingesting, standardising, storing, and computing energy-related data.

This package contains the runtime API and module system: the piece you need for route 1 in the
[root README](../../README.md), running a single energy community yourself. If you'd rather
start from a ready-made repo than from this package directly, see
[cofy-api-template](https://github.com/EnergieID/cofy-api-template).

## Install

```sh
pip install "cofy-api[all]"
```

Cofy is modular — install only what you need via [extras](https://packaging.python.org/en/latest/specifications/dependency-specifiers/#extras).
Each module has an extra of its own name, and each integration providing data for those modules has one too, so
you only install the libraries of the sources you use. Example — the tariff module with ENTSO-E prices:

```sh
pip install "cofy-api[tariff,entsoe]"
```

| Module extras | Integration extras |
|---|---|
| `tariff`, `production`, `simultaneity`, `directive`, `billing`, `members` | `entsoe`, `energy-cost`, `energyid`, `acc` |

## Quick start

Create an app.py file with a minimal Cofy API:

```python
from cofy.api import CofyAPI
from cofy.integrations.entsoe import EntsoeDayAheadTariffSource
from cofy.modules.tariff import TariffModule

app = CofyAPI()
app.register_module(TariffModule(source=EntsoeDayAheadTariffSource(api_key="YOUR_ENTSOE_KEY"), name="entsoe"))
```

Run it:

```sh
fastapi dev app.py
```

The API is now available at `http://127.0.0.1:8000` with interactive docs at `/docs`.

## Sources and families

Every timeseries source belongs to a family describing what it produces, and every field taking a source accepts
one family. A tariff module only takes prices, a directive only takes numeric values, and so on, so only valid
combinations can be configured.

```
TimeseriesSource
├── NumericSource           cofy.modules.timeseries
│   ├── PriceSource         cofy.modules.tariff
│   ├── ProductionSource    cofy.modules.production
│   ├── NetVolumeSource     cofy.modules.simultaneity
│   └── RatioSource         cofy.modules.simultaneity
├── DirectiveSeriesSource   cofy.modules.directive
└── BoundarySource          cofy.modules.directive
```

A source of your own subclasses the family it belongs to, and implements `_fetch_timeseries`:

```python
class MyPriceSourceSettings(PriceSourceSettings):
    type: Literal["my_price"] = "my_price"


class MyPriceSource(PriceSource, settings=MyPriceSourceSettings):
    async def _fetch_timeseries(self, start, end, resolution, **kwargs) -> Timeseries: ...
```

A family of your own is an abstract subclass of the family it narrows, and a field accepting it is typed with its
union, which is published once every type is registered:

```python
class TemperatureSourceSettings(NumericSourceSettings):
    type: Literal["temperature_source"] = "temperature_source"


class TemperatureSource(NumericSource, settings=TemperatureSourceSettings, abstract=True): ...


if TYPE_CHECKING:
    AnyTemperatureSourceSettings = TemperatureSourceSettings


class HeatingModuleSettings(TimeseriesModuleSettings):
    type: Literal["heating"] = "heating"
    source: "AnyTemperatureSourceSettings"
```

Every family's union also accepts a reference to a source resource, so a field accepts one family: for sources of two
families that aren't nested, use their common ancestor.

## Caching

Any source can cache what it fetches, in memory and in aligned chunks of time, by giving it a `cache`:

```yaml
source:
  type: acc_forecast
  ean: "541448800000000000"
  credentials: ${ACC_CREDENTIALS}
  cache:
    max_age: PT15M  # defaults to how long the source says its data stays valid
```

From Python, pass `cache=CacheSettings(...)` to the source's constructor. A source implements `_fetch_timeseries`, and
takes `cache` and passes it on to `super().__init__`; the public `fetch_timeseries` serves from the cache when there is
one, and a source can override it to cache differently.

## Secrets

Credentials live in a community's `secrets`, and every field needing one references a secret with
`{type: secret, name: ...}` instead of holding it. A secret's value is never sent back by the management API.

```yaml
secrets:
  - name: entsoe_key
    value: my-entsoe-api-key

modules:
  - type: tariff
    name: prices
    source: { type: entsoe_day_ahead, api_key: { type: secret, name: entsoe_key } }
```

A settings field of your own holding a credential is typed `Secret`; its object is built with the secret's value. Built
from Python, objects take the value itself, as before.

## Resources

A value used in several places - a source, a tariff - can be configured once as a named resource and referenced by name
wherever one of its kind fits. A referenced source is built once, so every module referencing it shares its cache.

```yaml
resources:
  - type: source
    name: day_ahead
    value:
      type: entsoe_day_ahead
      api_key: { type: secret, name: entsoe_key }
      cache: {}

modules:
  - type: tariff
    name: prices
    source: { type: resource, name: day_ahead }
```

A reference to a source resource fits wherever the source it holds would. Energy-cost tariffs accept references too, and
a field of your own opts in with `Annotated[..., Referable("<kind>")]`.

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
