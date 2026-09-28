# Cofy API demo (settings file)

The same instance as [demo-cofy-api](../demo_cofy_api), built instead from a declarative
[settings.yaml](settings.yaml) via `CofyAPI.create(...)` (`FromSettingsMixin`). `${VAR}`
placeholders in the file are filled in from the environment before it's parsed, so secrets
stay out of the committed config. See [main.py](main.py).

This is a worked example of route 1 in the [root README](../../README.md) - one community,
self-hosted, configured through a settings file rather than Python code. To start your own,
fork [cofy-api-template](https://github.com/EnergieID/cofy-api-template), or see
[packages/api](../../packages/api) for the package this demo is built from.

## Running

```sh
task demo-cofy-api-settings
```

The API is available at http://127.0.0.1:8000 with docs at `/docs`.

## Deltawind simultaneity directive

The `deltawind` directive module is the proof of concept for the Deltawind pilot. It fetches
forecasts per EAN from ACC's Connection Usage Service (`acc_forecast`), turns them into total
consumption as a percentage of total production (`simultaneity`), and encodes that as directive
steps. It needs `ACC_CREDENTIALS` (the service-account JSON from ACC, on a single line) and
`ACC_EAN_1`; add more members to `sources` in [settings.yaml](settings.yaml) for more connections.

## Data

`data/` holds committed, read-only example config that `main.py` loads at startup (the modules
registered from `settings.yaml` are configured there directly). Nothing here is written to at
runtime.
