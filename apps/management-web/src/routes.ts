import { html } from "lit";

import type { RouteDefinition } from "./router.js";
import "./pages/communities-page.js";
import "./pages/module-page.js";
import "./pages/modules-page.js";
import "./pages/new-module-page.js";

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
    path: "/c/:slug",
    render: ({ slug }) => html`<cofy-modules-page .slug=${slug}></cofy-modules-page>`,
  },
  newModule: {
    path: "/c/:slug/new",
    render: ({ slug }) => html`<cofy-new-module-page .slug=${slug}></cofy-new-module-page>`,
  },
  module: {
    path: "/c/:slug/:type/:name",
    render: ({ slug, type, name }) =>
      html`<cofy-module-page .slug=${slug} .moduleId=${{ type, name }}></cofy-module-page>`,
  },
} as const satisfies Record<string, RouteDefinition>;

/** The name of a page, for navigating and linking. */
export type RouteName = keyof typeof routes;
