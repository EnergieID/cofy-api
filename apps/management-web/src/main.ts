// Web Awesome's theme, native-element styles and utility classes. First, so that everything
// after it - including the app's own rules - wins on ordinary cascade order. Its component
// styles sit in `@layer wa-component`, which unlayered CSS beats regardless.
import "@awesome.me/webawesome/dist/styles/webawesome.css";

import "@awesome.me/webawesome/dist/components/page/page.js";

import { provide } from "@lit/context";
import { AllowedModulesStore, ApiClient, CommunityStore, ModuleStore } from "@cofy/frontend-sdk";
import { StateController } from "@dodona/lit-state";
import {
  ThemeState,
  allowedModulesStoreContext,
  communityStoreContext,
  createI18n,
  i18nContext,
  moduleStoreContext,
  nativeStyles,
  themeStateContext,
  utilityStyles,
  yamlBackend,
} from "@cofy/web-components";
import "@cofy/web-components";
import { LitElement, css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";

import { crumbStateContext, routeStateContext } from "./context.js";
import { useLocalIcons } from "./icons.js";
import { APP_NAMESPACE, LANGUAGES } from "./i18n.js";
import { CrumbState } from "./states/crumb-state.js";
import { RouteState } from "./states/route-state.js";
import { routes } from "./routes.js";
import "./styles.css";
import "./brand.css";
import "@cofy/web-components/theme/syntax.css";

// Before any component renders, so no icon request is ever made.
useLocalIcons();

// Awaited before anything renders. `yamlBackend` fetches translations rather than bundling
// them, so a render that beat it would put raw keys on screen - one await is cheaper than a
// loading state in every component. The choice of backend is the app's, not the library's: a
// deployment could pass `init: { resources: {...} }` instead and skip fetching entirely.
const i18n = await createI18n({
  supportedLanguages: LANGUAGES,
  namespaces: [APP_NAMESPACE],
  backend: yamlBackend(),
});

// Puts the colour scheme on the root element and keeps following the operating system while
// the reader has not chosen otherwise. The brand colour is `brand.css`, not code.
const theme = new ThemeState();
theme.start();

/**
 * The console shell.
 *
 * It owns the stores, the route and the breadcrumb trail, provides them to the tree, and
 * renders the header plus whatever the route table returns. It knows about no individual
 * page: adding one is a new module and one entry in `routes.ts`.
 *
 * The stores, theme and translations are constructed here rather than imported as singletons,
 * which is what lets the components be embedded in someone else's app against a different
 * backend, theme and language.
 *
 * It does not extend `CofyElement` the way the pages do: an element that both provides and
 * consumes a context is deliberately skipped by its own provider, so the shell reads the
 * instance it built directly.
 */
@customElement("cofy-app")
export class CofyApp extends LitElement {
  public static override styles = [
    nativeStyles,
    utilityStyles,
    css`
      :host {
        display: block;
        min-block-size: 100vh;
      }
      .brand {
        font-weight: var(--wa-font-weight-semibold);
        text-decoration: none;
        font-size: var(--wa-font-size-l);
      }
      .brand .sub-brand {
        color: var(--wa-color-text-quiet);
        font-size: var(--wa-font-size-m);
        font-weight: var(--wa-font-weight-normal);
      }
      .crumbs {
        align-items: end;
        gap: var(--wa-space-2xl);
      }
      /* The chrome runs full width, but what it says lines up with the content under it. */
      .measure {
        max-inline-size: 60rem;
        margin-inline: auto;
        inline-size: 100%;
      }
      .content {
        padding: var(--wa-space-l);
      }
    `,
  ];

  private readonly api = new ApiClient();

  @provide({ context: communityStoreContext })
  public communities = new CommunityStore(this.api);

  @provide({ context: moduleStoreContext })
  public modules = new ModuleStore(this.api);

  @provide({ context: allowedModulesStoreContext })
  public allowedModules = new AllowedModulesStore(this.api);

  @provide({ context: routeStateContext })
  public routeState = new RouteState(routes);

  @provide({ context: crumbStateContext })
  public crumbState = new CrumbState();

  @provide({ context: i18nContext })
  public i18n = i18n;

  @provide({ context: themeStateContext })
  public theme = theme;

  public readonly stateController = new StateController(this);

  public override connectedCallback(): void {
    super.connectedCallback();
    this.routeState.start();
  }

  public override disconnectedCallback(): void {
    super.disconnectedCallback();
    this.routeState.stop();
  }

  public override render(): TemplateResult {
    return html`
      <wa-page>
        <!-- The console has no navigation, so the mobile hamburger has nothing to toggle.
             Overriding the slot suppresses it - and with it the only thing on the page that
             would fetch an icon from Font Awesome's CDN at runtime. -->
        <span slot="navigation-toggle"></span>

        <!-- wa-split pushes the settings control to the far end, which is what a raw
             framework class used to do here. No navigation beyond the breadcrumb trail yet,
             so it sits alongside the brand rather than in its own row - a dedicated subheader
             would spend a row of vertical space it does not need. -->
        <header slot="header" class="wa-split measure">
          <div class="wa-cluster crumbs">
            <a class="brand" href="#/">
              <wa-icon name="brand" library="cofy"></wa-icon>
              <span class="wa-desktop-only">${this.t("product")} <span class=sub-brand>${this.t("subtitle")}</span></span>
            </a>
            <cofy-breadcrumbs .crumbs=${this.crumbState.crumbs}></cofy-breadcrumbs>
          </div>
          <cofy-settings-panel></cofy-settings-panel>
        </header>

        <div class="content measure">
          ${this.routeState.render() ?? html`<p>${this.t("notFound", { path: this.routeState.path })}</p>`}
        </div>
      </wa-page>
    `;
  }

  private t(key: string, params?: Record<string, unknown>): string {
    return this.i18n.t(key, { ns: APP_NAMESPACE, ...params });
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-app": CofyApp;
  }
}
