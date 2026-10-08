import { html } from "lit";

import type { RouteDefinition } from "./router.js";
import "./pages/communities-page.js";
import "./pages/module-page.js";
import "./pages/community-page.js";
import "./pages/new-module-page.js";
import "./pages/new-resource-page.js";
import "./pages/resource-page.js";

/**
 * Every page, keyed by the name the rest of the app navigates by.
 *
 * Adding a page means writing its module and adding one entry here: the name, the path it
 * answers, and what to render. `render` receives only the captured path parameters;
 * everything else - stores, routing, the breadcrumb trail - a page consumes from context.
 *
 * Matching runs in declaration order, so a pattern with a literal segment must come before
 * one whose parameter would also match it.
 */
export const routes = {
  communities: {
    path: "/",
    render: () => html`<cofy-communities-page></cofy-communities-page>`,
  },
  modules: {
    path: "/communities/:slug",
    render: ({ slug }) => html`<cofy-community-page .slug=${slug} tab="modules"></cofy-community-page>`,
  },
  resources: {
    path: "/communities/:slug/resources",
    render: ({ slug }) => html`<cofy-community-page .slug=${slug} tab="resources"></cofy-community-page>`,
  },
  secrets: {
    path: "/communities/:slug/secrets",
    render: ({ slug }) => html`<cofy-community-page .slug=${slug} tab="secrets"></cofy-community-page>`,
  },
  tokens: {
    path: "/communities/:slug/tokens",
    render: ({ slug }) => html`<cofy-community-page .slug=${slug} tab="tokens"></cofy-community-page>`,
  },
  grants: {
    path: "/communities/:slug/grants",
    render: ({ slug }) => html`<cofy-community-page .slug=${slug} tab="grants"></cofy-community-page>`,
  },
  newModule: {
    path: "/communities/:slug/modules/new",
    render: ({ slug }) => html`<cofy-new-module-page .slug=${slug}></cofy-new-module-page>`,
  },
  newResource: {
    path: "/communities/:slug/resources/new",
    render: ({ slug }) => html`<cofy-new-resource-page .slug=${slug}></cofy-new-resource-page>`,
  },
  resource: {
    path: "/communities/:slug/resources/:name",
    render: ({ slug, name }) => html`<cofy-resource-page .slug=${slug} .name=${name}></cofy-resource-page>`,
  },
  module: {
    path: "/communities/:slug/modules/:type/:name",
    render: ({ slug, type, name }) =>
      html`<cofy-module-page .slug=${slug} .moduleId=${{ type, name }}></cofy-module-page>`,
  },
} as const satisfies Record<string, RouteDefinition>;

/** The name of a page, for navigating and linking. */
export type RouteName = keyof typeof routes;
