# Cofy Runner

Serves a directory of community settings, each `<slug>.yaml` as the Cofy API it describes, under
`/<slug>/`. It is what runs the communities that the [management API](../management-api)
configures, in route 2 of the [root README](../../README.md); the two only share the settings
directory, which the runner never writes.

The directory is checked every few seconds. A community whose file changed is built again and
swapped in while the rest keep serving; settings that fail to build are logged, and the community
keeps serving what it served before.

## Health

Each community's API answers `GET /<slug>/health` without a token, with the revision of the
settings it runs: `{"status": "ok", "revision": 12}`. Compared with the revision in the settings
file, that tells whether its latest settings are in use. A community whose settings have never
built answers `503`; one the runner doesn't serve, `404`. What went wrong is only in the log.

The revision is the settings' own `revision`, which the management API raises on every change,
and which a community's API also reports as the build metadata of its version, as in `1.4.0+12`.

## Configuration

| Variable                    | Meaning                                                                |
|-----------------------------|------------------------------------------------------------------------|
| `COFY_RUNNER_DIRECTORY`     | The directory of community settings to serve.                          |
| `COFY_RUNNER_COMMUNITIES`   | Optional, the slugs to serve, comma separated; every community by default. |
| `COFY_RUNNER_POLL_INTERVAL` | Optional, how often to check for changes, as an ISO 8601 duration; `PT2S` by default. |

Limiting the communities lets several runners share one directory, each serving some of them.

Behind a proxy that serves the runner under a path prefix, strip the prefix and pass it to
uvicorn as `--root-path` (or `UVICORN_ROOT_PATH`), so the communities' API docs point at where
they really are.

## Development

```sh
uv sync --group dev
COFY_RUNNER_DIRECTORY=../../apps/demo_multitenant/.data/communities poe run
```

Common commands:

```sh
poe test
poe lint
poe format
poe check
```
