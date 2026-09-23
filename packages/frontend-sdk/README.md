# @cofy/frontend-sdk

A typed client and reactive state stores for the [Cofy Management API](../management-api), for
anyone building their own UI on top of it (route 3 in the [root README](../../README.md)). If
you just want a management console, the default one -
[apps/management-web](../../apps/management-web) - already uses this package; you likely only
need this directly if you're building a custom console with
[@cofy/web-components](../web-components) or your own components.

## What's in it

- `ApiClient` - a thin wrapper around [`openapi-fetch`](https://openapi-ts.dev/openapi-fetch/),
  typed from the management API's own OpenAPI document (`src/generated/api.ts`). Every method
  resolves with the response body or throws a `ProblemError` carrying the
  [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) problem document the API returned - a
  wrong path, a missing parameter, or a mistyped body is a compile error, not a runtime one.
- `CommunityStore`, `ModuleStore`, `AllowedModulesStore` - reactive state built on
  [`@dodona/lit-state`](https://github.com/dodona-edu/lit-state), each wrapping one part of the
  API (communities, a community's modules, which module types are available) as loadable,
  observable state instead of one-off requests.
- `ModuleDraft`, `EditableValue` - in-progress edits to a module's settings, validated against
  the module's JSON Schema as you type, before anything is sent to the API.
- `validate`, `narrowToInstance` - JSON Schema validation helpers used by the drafts above and
  reusable on their own.

## Install

Not published to a registry yet - consume it as a workspace dependency the way
[apps/management-web](../../apps/management-web) does, or build it and reference
`packages/frontend-sdk/dist` from your own app:

```sh
npm install
npm run build
```

## Usage

```ts
import { ApiClient, CommunityStore } from "@cofy/frontend-sdk";

const api = new ApiClient({ baseUrl: "http://127.0.0.1:8000" });
const communities = new CommunityStore(api);
await communities.load();
```

`ApiClient` defaults to the page's own origin (`baseUrl: "/"`), which is what lets a console
served by the management API itself (see
[apps/demo_multitenant](../../apps/demo_multitenant)) talk to it with no CORS setup and no base
URL to configure.

## Regenerating the API types

`src/generated/api.ts` is generated from the management API's own OpenAPI document, not written
by hand:

```sh
npm run generate
```

Run it after changing any endpoint in [packages/management-api](../management-api). It shells
out to that package via `uv`, so that package's dependencies need to be installed first
(`uv sync` there).

## Development

```sh
npm install
npm test
npm run check
npm run lint
```
