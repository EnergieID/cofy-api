# Cofy Management API

Cofy Management API provides endpoints to manage one or more Cofy configurations.

It depends on cofy-api and uses its module settings models for polymorphic module configuration.

## Configuration

`COFY_MANAGEMENT_DATA_DIR` must be set to a writable directory where community configs are
stored - there is no built-in default. See [apps/demo_multitenant](../../apps/demo_multitenant)
for a worked example, including a reset script that restores its data to committed defaults.

## Development

```sh
uv sync --group dev
poe run
```

Common commands:

```sh
poe test
poe lint
poe format
poe check
```
