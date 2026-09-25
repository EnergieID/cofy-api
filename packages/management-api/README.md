# Cofy Management API

Cofy Management API provides endpoints to manage one or more Cofy configurations.

It depends on cofy-api and uses its module settings models for polymorphic module configuration.

This is the backend for route 2 in the [root README](../../README.md), hosting more than one
community behind a single management layer. It's a plain CRUD/config API with no UI of its own -
pair it with [packages/frontend-sdk](../frontend-sdk) and
[packages/web-components](../web-components) (or the default console,
[apps/management-web](../../apps/management-web)) for a UI, or drive it directly if you're
building your own tooling. [apps/demo_multitenant](../../apps/demo_multitenant) shows the whole
stack running together.

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
