**Cofy Cloud** is an open-source modular framework for ingesting, standardising, storing, and computing energy-related data, designed to run anywhere from local deployments to cloud environments.

Right now this is very much a work in progress.
With the development of a firts proof of concept. This it not ready for production use and the api is likely to change significantly in the near future.

## Setup
### Install
*TODO*
### Configure
*TODO*
### Development
We use [astral](https://docs.astral.sh/) python tooling for our development environment.
We use [poethepoet](https://poethepoet.natn.io) to define some essential tasks.
The demo run task is also available as vscode execution task, making it easy to run and debug the demo application from within vscode.

#### Install/update dependencies:
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

#### Run development demo application:
Our demo application uses some API keys for external services. You can provide these `local.settings.json` file in the root of the repository, following the structure of `local.settings.example.json`.

```sh
poe demo
```

#### Code style checks:
```sh
poe lint    # Check code style
poe format  # Format code
poe check   # Run type checks
```

#### Run tests:
TODO

#### Build & publish
TODO
