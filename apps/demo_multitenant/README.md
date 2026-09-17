# Multitenant demo

Runs the management API together with the management console, so several communities can be
configured and operated through the UI. Demonstrates hosting more than one `cofy-api`
configuration behind a single management layer.

## Running

```sh
task demo-multitenant-reset   # first run only, or whenever you want to start over
task demo-multitenant-api     # management API on :8000
task demo-multitenant-web     # console dev server on :5173, proxying to the API
```

## Data

`seed/` holds the committed default communities. `task demo-multitenant-reset` copies it into
`.data/`, which is git-ignored and is what the management API actually reads and writes while
the demo runs (`COFY_MANAGEMENT_DATA_DIR`, set by the `demo-multitenant-api` task). Run the
reset task again any time to discard local changes and start from the committed defaults.
