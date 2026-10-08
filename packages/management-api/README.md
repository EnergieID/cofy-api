# Cofy Management API

Cofy Management API provides endpoints to manage one or more Cofy configurations.

It depends on cofy-api and uses its module settings models for polymorphic module configuration.

This is the backend for route 2 in the [root README](../../README.md), hosting more than one
community behind a single management layer. It's a plain CRUD/config API with no UI of its own -
pair it with [packages/frontend-sdk](../frontend-sdk) and
[packages/web-components](../web-components) (or the default console,
[apps/management-web](../../apps/management-web)) for a UI, or drive it directly if you're
building your own tooling. [apps/demo_multitenant](../../apps/demo_multitenant) shows the whole
stack running together.

## Configuration

`COFY_MANAGEMENT_DATA_DIR` and `COFY_MANAGEMENT_COMMUNITIES_DIR` must be set to writable
directories - there is no built-in default. The first holds who may do what in
`access/users.yaml`, the second the community configs, as `<slug>.yaml`. They are apart so the
community configs can live elsewhere: the [runner](../runner) serving them needs nothing else. See [apps/demo_multitenant](../../apps/demo_multitenant)
for a worked example, including a reset script that restores its data to committed defaults.

Every write replaces a file whole, renaming a new one over it, so whatever reads the files without
going through this API never sees one half-written; the locks writes take are on hidden `.lock`
files beside them. A community config's `revision` is raised by one on every write; raise it when
editing one by hand too, so the change shows as a new revision.

`COFY_MANAGEMENT_COMMUNITIES_URL` must be set to where the communities' APIs are served, such as
`https://cofy.example/communities` - by the [runner](../runner), or anything else serving each
under its slug. A community's `api_url` is its slug under it, and
`/management/communities/{slug}/status` asks its `/health` for the revision it runs, answering in
one of three states: `live` when that is the saved one, `pending` while it is an earlier one - for
a few seconds after a change, or for as long as the change fails to apply - and `unavailable`. Why
is in the log of what serves it, not in the answer.

## Logging in

Every route needs a login, except the login itself. The API doesn't keep accounts: it logs people
in through an OpenID Connect provider of your choice - Keycloak, Authentik, Entra ID, Duende
IdentityServer, ... - as a confidential client using the authorization code flow with PKCE, and
keeps who logged in in a signed, HTTP-only session cookie. The browser never holds a token.

| Variable                             | Meaning                                                       |
|--------------------------------------|---------------------------------------------------------------|
| `COFY_MANAGEMENT_OIDC_ISSUER`        | The provider's issuer URL, where its discovery document is.   |
| `COFY_MANAGEMENT_OIDC_CLIENT_ID`     | This API's client id at the provider.                         |
| `COFY_MANAGEMENT_OIDC_CLIENT_SECRET` | Its client secret.                                            |
| `COFY_MANAGEMENT_OIDC_SCOPES`        | Optional, `openid profile email` by default.                  |
| `COFY_MANAGEMENT_SESSION_SECRET`     | A long random value the session cookie is signed with.        |
| `COFY_MANAGEMENT_SESSION_LIFETIME`   | Optional, how long a login lasts, as an ISO 8601 duration; `PT8H` by default. |
| `COFY_MANAGEMENT_SECURE_COOKIES`     | Optional, `true` by default; `false` only to develop over plain HTTP. |

The API won't start without the first four. At the provider, register the redirect URI
`https://<host>/auth/callback`, and have it report a verified `email` claim, in the ID token or
from its userinfo endpoint.

Behind a TLS-terminating proxy, run uvicorn with `--proxy-headers` so that callback URL is built
with the public scheme and host.

### Who may do what

Everyone who may do something is listed in `access/users.yaml` in the data directory, each with
the role they have in each community:

```yaml
users:
  - email: you@example.com
    system_admin: true
  - email: ann@example.com
    grants:
      demo: community_admin
```

- **System admins** may do everything. Who they are is edited in this file on the server, not
  through the API.
- **Community admins** may manage the communities they are granted, including who else has
  access to them, through `/management/communities/{slug}/grants`. Deleting a community takes
  away every role in it.

Access is granted to an email, since that is all anyone knows of a person who hasn't logged in yet.
At that person's first login with a verified email, their identity at the provider is written
in beside it and matched on from then on, so changing their email there neither loses their
access nor hands it to whoever gets the address next.

A permission is an action - `read` or `write` - on a subject of a community: its own settings,
its modules, resources, secrets, grants, or the types it may use (`cofy/management/auth/access.py`). A role is a
set of permissions, so adding one - a viewer, say - is a matter of listing what it may do.

Every route is registered with the rule of `cofy/management/policies/` guarding it, and a router
refuses a route without one. One policy covers every subject alike: seeing it takes `read` on it,
changing it `write`. A subject whose rules differ gets a subclass, as communities do, which only
a system admin may delete. System admins are let through every rule.

`/auth/me` reports what the person logged in may do, per community, and for a system admin also
outside any one community (`slug: null`), such as creating communities. Listing communities takes
being able to see at least one; anyone else is refused, as for a community they can't see.

### EnergyID

EnergyID's identity server is a Duende IdentityServer, configured in its database. The
management API needs a client there with:

- a client secret, the `authorization_code` grant, PKCE required and consent off;
- the redirect URI `https://<host>/auth/callback`, and `https://<host>/` as post-logout redirect URI;
- the scopes `openid`, `profile` and `email`, with the `email` identity resource present.

Each such client counts towards the clients the Duende license allows.

For development, `task dev-idp` runs a local provider built on Duende as well - see
[apps/demo_multitenant](../../apps/demo_multitenant).

## Development

```sh
uv sync --group dev
poe run
```

Common commands:

```sh
poe test
poe lint
poe format
poe check
```
