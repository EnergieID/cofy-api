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

## Docker

`Dockerfile` builds the management API and the console into a single image: the console is
served by the API itself (same origin, so no CORS or base URL to configure - see
`COFY_MANAGEMENT_STATIC_DIR` in `packages/management-api/src/cofy/management/main.py`).

```sh
task demo-multitenant-docker
```

Runs the same build and run as:

```sh
docker build -f apps/demo_multitenant/Dockerfile -t cofy-management-demo .
docker run -p 8080:8080 -v cofy-management-data:/data cofy-management-demo
```

Build from the repo root, since the image needs sources from several packages. `/data` is
where community configs (and the modules they reference) live - mount a volume there so they
survive a redeploy instead of resetting. On first boot, an empty `/data` is seeded from
`seed/`; once anything exists there, it's left alone. The container reads `PORT` (defaults to
`8080`, matching most cloud platforms, including Scaleway's container runtime) and honors a
`VERSION` build arg for `APP_VERSION`.

## Production deploy

`.github/workflows/deploy-scaleway.yml` builds the image, pushes it to `ghcr.io`, and deploys
it to a Scaleway instance on every push to `main`. There, `docker-compose.yml` runs it behind
`caddy` (`Caddyfile`) for TLS: `app` has no published port at all, so the only way in from
outside is through Caddy's automatic Let's Encrypt HTTPS on 80/443 - see
[deploy-scaleway.yml](../../.github/workflows/deploy-scaleway.yml) for exactly what it copies
to the server and runs. `caddy_data`/`caddy_config` (the issued certificate and Caddy's own
state) are named volumes, so a redeploy doesn't force reissuing the certificate.
