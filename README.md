# Cofy Cloud

**Cofy Cloud** is an open-source modular framework for ingesting, standardising, storing, and computing energy-related data, designed to run from local setups to cloud deployments.

This repository uses a monorepo structure with separate packages.

## Structure

- Runtime API package: [packages/api](packages/api)
- Management API package: [packages/management-api](packages/management-api)
- Demo application: [demo](demo)
- Architecture and planning specs: [specs](specs)

## Quick Start (Repository)

Install root developer tooling:

```sh
uv sync --group dev
```

Run the demo API:

```sh
poe demo
```

Run the management API:

```sh
poe management
```

The demo API is available at http://127.0.0.1:8000 with docs at /docs.

## Development Commands

```sh
poe test
poe lint
poe format
poe check
```

## Package Documentation

- API package README: [packages/api/README.md](packages/api/README.md)
- Management package README: [packages/management-api/README.md](packages/management-api/README.md)

## Notes On Near-Term Direction

Current development is focused on strengthening the modular Python runtime and management APIs. Future additions (frontend components, orchestrator, broker integrations, and visualization services) are tracked in [specs](specs) and will be added incrementally.
