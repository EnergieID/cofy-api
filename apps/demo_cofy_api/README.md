# Cofy API demo (Python)

A `cofy-api` instance assembled in Python: modules and sources are constructed directly and
registered on a `CofyAPI()`. See [main.py](main.py).

This is a worked example of route 1 in the [root README](../../README.md) - one community,
self-hosted. To start your own instead of reading this one, fork
[cofy-api-template](https://github.com/EnergieID/cofy-api-template), or see
[packages/api](../../packages/api) for the package this demo is built from.

## Running

```sh
task demo-cofy-api
```

The API is available at http://127.0.0.1:8000 with docs at `/docs`.

## Data

`data/` holds committed, read-only example config (tariffs, a members CSV, a monthly index) that
`main.py` loads at startup. Nothing here is written to at runtime.
