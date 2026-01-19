**Cofy Cloud** is an open-source modular framework for ingesting, standardising, storing, and computing energy-related data, designed to run anywhere from local deployments to cloud environments.

Right now this is very much a work in progress, with the specifications still being defined and reworked in `specs/`.

## Setup
### Install
*TODO*
### Configure
*TODO*
### Development
We use [astral](https://docs.astral.sh/) python tooling for our development environment.

Install/update dependencies:
```sh
uv sync
```
Run development demo application:
```sh
poe demo
```
Code style checks:
```sh
poe lint    # Check code style
poe format  # Format code
poe check   # Run type checks
```