# Cofy Cloud

Cofy Cloud is an open-source platform for energy communities. It collects and standardises
energy data — meter readings, local production, tariffs — and turns it into the billing and
reporting a community needs to run itself. It's free, it's yours to host, and it's modular: you
switch on only the parts your community actually needs.

## Not sure where to start?

The quickest way to find out if Cofy fits your community, or to get help setting it up, is to
[open a GitHub issue](https://github.com/EnergieID/cofy-api/issues). That's true whether you
have an IT team behind you or not — we'd rather help you get it right than have you guess.

If you (or someone helping you) are comfortable running your own software, read on: there are
three ways to run Cofy, roughly from least to most setup.

## 1. One community, self-hosted

Run a single Cofy API for your own energy community: you register the modules you need (a
tariff, your members list, production data, ...) and get back a data API for that community.
This is the simplest route and needs no separate database or UI.

The fastest way to start is [cofy-api-template](https://github.com/EnergieID/cofy-api-template),
a template repository set up to fork and run. To build it up yourself instead, or to see what a
Cofy API actually looks like in code, start with the runtime package:
[packages/api](packages/api) and its two worked examples,
[apps/demo_cofy_api](apps/demo_cofy_api) (assembled directly in Python) and
[apps/demo_cofy_api_settings](apps/demo_cofy_api_settings) (assembled from a settings file).

## 2. Several communities, with a management UI

If you're hosting Cofy on behalf of more than one community — a federation, a cooperative, a
software partner — Cofy also ships a management API and a web console to create and configure
each community's setup without touching code per community.

[apps/demo_multitenant](apps/demo_multitenant) shows how the management API and the console fit
together, how to run them locally, and how to build and deploy the combined Docker image
yourself.

## 3. A fully custom setup

Every piece above is its own package, so you can take only what you need and build around it:

- [packages/api](packages/api) — the runtime module system used by route 1
- [packages/management-api](packages/management-api) — CRUD API for one or more community
  configs, used by route 2
- [packages/frontend-sdk](packages/frontend-sdk) — a typed TypeScript client and reactive state
  stores for the management API
- [packages/web-components](packages/web-components) — Lit UI building blocks (config forms, a
  YAML editor, layout) for building your own management console
- [apps/management-web](apps/management-web) — the default console built from the two packages
  above; fork it, or use it as a reference for your own

Each has its own README with install and usage instructions.

## Repository structure

- Runtime API package: [packages/api](packages/api)
- Management API package: [packages/management-api](packages/management-api)
- Frontend SDK package: [packages/frontend-sdk](packages/frontend-sdk)
- Web components package: [packages/web-components](packages/web-components)
- Default management console: [apps/management-web](apps/management-web)
- Demo applications: [apps/demo_cofy_api](apps/demo_cofy_api),
  [apps/demo_cofy_api_settings](apps/demo_cofy_api_settings),
  [apps/demo_multitenant](apps/demo_multitenant)
- Architecture and planning specs: [specs](specs)

## Quick start (this repository)

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and
[Task](https://taskfile.dev/installation/), used to run cross-package commands. The frontend
tasks also expect [Node](https://nodejs.org/) (see [.nvmrc](.nvmrc) for the version this repo
targets).

Four demo deployments are available, each usable as a worked example or for local development:

```sh
task demo-cofy-api             # cofy-api assembled in Python
task demo-cofy-api-settings    # cofy-api assembled from a settings file
task demo-multitenant-reset    # first run only: seed the multitenant demo's local data
task demo-multitenant-api      # management API, backing the multitenant demo
task demo-multitenant-web      # management console, talking to the API above
```

The `demo-cofy-api*` tasks serve their API at http://127.0.0.1:8000 with docs at `/docs`. See
each app's own README for details.

## Development commands

Root-level commands run the tasks for every package (via [Task](https://taskfile.dev), see
[Taskfile.yml](Taskfile.yml)):

```sh
task install   # install the frontend package dependencies (first run only)
task build     # build the frontend packages and the console
task test
task lint
task format
task check
```

## Getting help

Open a [GitHub issue](https://github.com/EnergieID/cofy-api/issues) — for questions, bug
reports, or help getting set up.

## License

[MIT](LICENSE)
