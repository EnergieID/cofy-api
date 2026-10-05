# Multitenant demo

Runs the management API together with the management console, so several communities can be
configured and operated through the UI. Demonstrates hosting more than one `cofy-api`
configuration behind a single management layer.

This is a worked example of route 2 in the [root README](../../README.md) - several
communities, with a management UI. It's the reference for anyone hosting Cofy on behalf of more
than one community: what to run, how the pieces talk to each other, and how to package and
deploy them.

## Running

```sh
task demo-multitenant-reset   # first run only, or whenever you want to start over
task dev-idp                  # local identity provider on :8081 (needs Docker)
task demo-multitenant-api     # management API on :8000
task demo-multitenant-web     # console dev server on :5173, proxying to the API
```

The API's settings come from `.env.local` at the repository root: copy the `COFY_MANAGEMENT_*`
lines from `.env.example`, which point at the local identity provider, and fill in the absolute
path of your checkout in `COFY_MANAGEMENT_DATA_DIR`.

Opening the console sends you to the local identity provider ([`apps/dev_idp`](../dev_idp/docker-compose.yml))
to log in. Its users all have the password `pwd`:

| User         | Can                                                       |
|--------------|-----------------------------------------------------------|
| `admin`      | everything: a system admin                                |
| `demo-admin` | manage the `demo` community                               |
| `nobody`     | log in, and see that there is nothing for them            |

## Data

`seed/` holds the committed defaults. `task demo-multitenant-reset` copies it into
`.data/`, which is git-ignored and is what the management API actually reads and writes while
the demo runs (`COFY_MANAGEMENT_DATA_DIR`, in `.env.local`). Run the
reset task again any time to discard local changes and start from the committed defaults.

It holds the community configs in `communities/`, and in `access/users.yaml` who may do what -
the system admins, and each person's role in each community. Logging in writes each person's
identity in beside their email, so that file changes as you use the demo too.

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
docker run --network host -v cofy-management-data:/data --env-file .env.local -e COFY_MANAGEMENT_DATA_DIR=/data cofy-management-demo
```

It logs in through `task dev-idp` too, which is why it runs on the host network: the container
and the browser must reach the identity provider at the same address.

Build from the repo root, since the image needs sources from several packages. `/data` is
where community configs (and the modules they reference) live - mount a volume there so they
survive a redeploy instead of resetting. On first boot, an empty `/data` is seeded from
`seed/`; once anything exists there, it's left alone. The container reads `PORT` (defaults to
`8080`, matching most cloud platforms, including Scaleway's container runtime) and honors a
`VERSION` build arg for `APP_VERSION`. `/data/access/users.yaml` is the file to edit to change who
the system admins are.

## Production deploy

`.github/workflows/deploy-scaleway.yml` builds the image, pushes it to `ghcr.io`, and deploys
it to a Scaleway instance on every push to `main`. There, `docker-compose.yml` runs it behind
`caddy` (`Caddyfile`) for TLS: `app` has no published port at all, so the only way in from
outside is through Caddy's automatic Let's Encrypt HTTPS on 80/443 - see
[deploy-scaleway.yml](../../.github/workflows/deploy-scaleway.yml) for exactly what it copies
to the server and runs. `caddy_data`/`caddy_config` (the issued certificate and Caddy's own
state) are named volumes, so a redeploy doesn't force reissuing the certificate.

The server needs two things the repository doesn't carry:

- a `.env` file next to `docker-compose.yml`, with the login configuration: `COFY_MANAGEMENT_OIDC_ISSUER`,
  `COFY_MANAGEMENT_OIDC_CLIENT_ID`, `COFY_MANAGEMENT_OIDC_CLIENT_SECRET` and a long random
  `COFY_MANAGEMENT_SESSION_SECRET`;
- your own entry in `/data/access/users.yaml`, with `system_admin: true`. It is seeded with the demo's local users,
  who can't log in through a real identity provider.

This is how EnergyID runs its own hosted instance, not a generally reachable image - the
`ghcr.io/energieid/cofy-api/management` package is private, so `docker-compose.yml` as
committed here only works for EnergyID's own deploy. To deploy your own copy the same way,
build and push the image to a registry you control (or reuse `task demo-multitenant-docker` to
build it locally), point `docker-compose.yml` at that image instead, and put your own
`Caddyfile` host names in front of it.
