import "@carbon/web-components/es/components/ui-shell/index.js";

import { provide } from "@lit/context";
import { AllowedModulesStore, ApiClient, CommunityStore, ModuleStore } from "@cofy/frontend-sdk";
import { StateController } from "@dodona/lit-state";
import { allowedModulesStoreContext, communityStoreContext, moduleStoreContext } from "@cofy/web-components";
import "@cofy/web-components";
import { LitElement, css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";

import { crumbStateContext, routeStateContext } from "./context.js";
import { CrumbState } from "./states/crumb-state.js";
import { RouteState } from "./states/route-state.js";
import { routes } from "./routes.js";
import { applyCarbonTheme } from "./theme.js";
import "./styles.css";

// Prepended to the document so the tokens are in place before the first component renders,
// and so a host stylesheet can still override them.
applyCarbonTheme();

/**
 * The console shell.
 *
 * It owns the stores, the route and the breadcrumb trail, provides them to the tree, and
 * renders the header plus whatever the route table returns. It knows about no individual
 * page: adding one is a new module and one entry in `routes.ts`.
 *
 * The stores are constructed here rather than imported as singletons, which is what lets the
 * components be embedded in someone else's app against a different backend.
 */
@customElement("cofy-app")
export class CofyApp extends LitElement {
  public static override styles = css`
    :host {
      display: block;
      min-block-size: 100vh;
      background: var(--cds-background);
      color: var(--cds-text-primary);
    }
    main {
      padding: 3rem 2rem 2rem;
      max-inline-size: 60rem;
      margin-inline: auto;
    }
    .trail {
      display: flex;
      align-items: center;
      padding-inline-start: 1rem;
    }
  `;

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
      <cds-header aria-label="Cofy management">
        <cds-header-name href="#/" prefix="Cofy">management</cds-header-name>
        <cofy-breadcrumbs class="trail" .crumbs=${this.crumbState.crumbs}></cofy-breadcrumbs>
      </cds-header>
      <main>${this.routeState.render()}</main>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-app": CofyApp;
  }
}
