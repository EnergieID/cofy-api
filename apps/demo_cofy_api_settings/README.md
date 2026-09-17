# Cofy API demo (settings file)

The same instance as [demo-cofy-api](../demo_cofy_api), built instead from a declarative
[settings.yaml](settings.yaml) via `CofyAPI.create(...)` (`FromSettingsMixin`). `${VAR}`
placeholders in the file are filled in from the environment before it's parsed, so secrets
stay out of the committed config. See [main.py](main.py).

## Running

```sh
task demo-cofy-api-settings
```

The API is available at http://127.0.0.1:8000 with docs at `/docs`.

## Data

`data/` holds committed, read-only example config that `main.py` loads at startup (the modules
registered from `settings.yaml` are configured there directly). Nothing here is written to at
runtime.
