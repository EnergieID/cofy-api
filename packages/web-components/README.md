# @cofy/web-components

Lit components for building a Cofy management console: config forms generated from JSON
Schema, a YAML editor, community and module lists, theming and translations. This is what
[apps/management-web](../../apps/management-web) is built from, and what you'd reach for to
build your own console instead (route 3 in the [root README](../../README.md)). It's built on
[Web Awesome](https://webawesome.com/) and depends on
[@cofy/frontend-sdk](../frontend-sdk) for its data.

## What's in it

- **Schema-driven forms** (`components/form/*`) - `CofyAnyForm` dispatches a JSON Schema node to
  the right field component (string, number, boolean, enum, object, list, dict, union, a
  secret, a raw YAML fallback) via a `FieldRegistry`. The registry is overridable per subtree
  (provide your own ahead of the built-ins through `fieldRegistryContext`), so a deployment can
  add a field for its own module types without forking the package.
- **Community and module management** (`components/community/*`, `components/module/*`) -
  `CofyCommunityList`, `CofyModuleList`, `CofyModuleEditor`, `CofyModuleCreate`: the pieces a
  console needs to list, create and edit communities and their modules against
  `@cofy/frontend-sdk`'s stores.
- **A YAML editor** (`components/editor/*`) - `CofyYamlEditor`, a CodeMirror-based editor with
  YAML syntax highlighting and lint diagnostics, backing the raw-YAML fallback form and
  anywhere else config needs hand-editing.
- **Theming** (`theme/*`) - `ThemeState` (light/dark/system, persisted), plus shared styles
  (`nativeStyles`, `utilityStyles`, `tableStyles`) built on Web Awesome's `--wa-*` tokens. See
  [apps/management-web/src/brand.css](../../apps/management-web/src/brand.css) for how a
  deployment sets its own brand colour - it's a set of CSS custom properties, no code or build
  step involved.
- **Translations** (`i18n/*`) - `createI18n`, `CofyI18n`, built on
  [i18next](https://www.i18next.com/). The library's own strings ship as YAML under
  [locales/](locales) rather than bundled into the JS, so a deployment can add a language or
  correct a translation by dropping in a file - no rebuild needed. `yamlBackend()` is the
  loader that reads them; see how [apps/management-web](../../apps/management-web) serves both
  its own and the library's locales from one origin.
- `CofyElement` - a small `LitElement` base most components extend, wiring up the contexts
  above.

## Install

Not published to a registry yet - consume it as a workspace dependency the way
[apps/management-web](../../apps/management-web) does, or build it and reference
`packages/web-components/dist`:

```sh
npm install
npm run build
```

`@awesome.me/webawesome`, `@cofy/frontend-sdk`, `@dodona/lit-state` and `lit` are peer
dependencies - your app supplies one copy of each, which is also what keeps their module-level
state (Lit's element registry, lit-state's recorder) from silently duplicating across two
copies of the same package.

## Usage

Provide the stores and shared state a component tree needs, then use the components in a
template:

```ts
import { provide } from "@lit/context";
import { ApiClient, CommunityStore } from "@cofy/frontend-sdk";
import { communityStoreContext } from "@cofy/web-components";
import "@cofy/web-components/components/community/cofy-community-list";

class MyConsole extends LitElement {
  private readonly api = new ApiClient({ baseUrl: "http://127.0.0.1:8000" });

  @provide({ context: communityStoreContext })
  public communities = new CommunityStore(this.api);
}
```

See [apps/management-web/src/main.ts](../../apps/management-web/src/main.ts) for the full set
of contexts a real console provides (stores, theme, i18n, routing state).

## Development

```sh
npm install
npm test
npm run check
npm run lint
```
