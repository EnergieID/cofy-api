# Cofy Cloud

**Cofy Cloud** is an open-source modular framework for ingesting, standardising, storing, and computing energy-related data, designed to run from local setups to cloud deployments.

This repository uses a monorepo structure with separate packages. Each package has its own README with more specific instructions.

## Structure

- Runtime API package: [packages/api](packages/api)
- Management API package: [packages/management-api](packages/management-api)
- Demo applications: [apps/demo_cofy_api](apps/demo_cofy_api), [apps/demo_cofy_api_settings](apps/demo_cofy_api_settings), [apps/demo_multitenant](apps/demo_multitenant)
- Architecture and planning specs: [specs](specs)

## Quick Start (Repository)

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and [Task](https://taskfile.dev/installation/), used to run cross-package commands.

Three demo deployments are available, each usable as a worked example or for local development:

```sh
task demo-cofy-api             # cofy-api assembled in Python
task demo-cofy-api-settings    # cofy-api assembled from a settings file
task demo-multitenant-reset    # first run only: seed the multitenant demo's local data
task demo-multitenant-api      # management API, backing the multitenant demo
task demo-multitenant-web      # management console, talking to the API above
```

The `demo-cofy-api*` tasks serve their API at http://127.0.0.1:8000 with docs at `/docs`. See
each app's own README for details.

## Development Commands

Root-level commands run the tasks for every package (via [Task](https://taskfile.dev), see [Taskfile.yml](Taskfile.yml)):

```sh
task test
task lint
task format
task check
```

## Package Documentation

- API package README: [packages/api/README.md](packages/api/README.md)
- Management package README: [packages/management-api/README.md](packages/management-api/README.md)

## Notes On Near-Term Direction

Current development is focused on strengthening the modular Python runtime and management APIs. Future additions (frontend components, orchestrator, broker integrations, and visualization services) are tracked in [specs](specs) and will be added incrementally.
