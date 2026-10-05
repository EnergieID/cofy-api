import { consume } from "@lit/context";
import { ProblemError } from "@cofy/frontend-sdk";
import type { SessionStore } from "@cofy/frontend-sdk";
import { CofyElement, sessionStoreContext } from "@cofy/web-components";
import type { Crumb } from "@cofy/web-components";
import type { TOptions } from "i18next";
import { html } from "lit";
import type { TemplateResult } from "lit";

import { crumbStateContext, routeStateContext } from "../context.js";
import type { RouteName } from "../routes.js";
import type { CrumbState } from "../states/crumb-state.js";
import type { RouteState } from "../states/route-state.js";
import { APP_NAMESPACE } from "../i18n.js";

/** What a page shows in place of itself to someone who may not see its community. */
const NO_ACCESS = new ProblemError(403, { status: 403, code: "forbidden" });

/**
 * What every page needs on top of {@link CofyElement}: the route to navigate by, the trail
 * to publish, and keeping a community's pages from those who may not see it.
 *
 * A subclass renders through {@link content}. One that belongs to a community has its `slug`, from
 * the route, and is shown the same "no access" a refused request shows instead of its content when
 * the person logged in may not see that community.
 *
 * A subclass implements {@link crumbs} and is done; the trail is published after each render,
 * which is late enough that reading a store here cannot race the render that subscribed to
 * it. A subclass overriding `updated` has to call `super.updated()` or its trail stops
 * updating.
 *
 * Pages translate out of the `app` namespace, since `components` belongs to the library.
 */
export abstract class CofyPage extends CofyElement {
  @consume({ context: routeStateContext, subscribe: true })
  public routes!: RouteState<RouteName>;

  @consume({ context: crumbStateContext, subscribe: true })
  public trail!: CrumbState;

  @consume({ context: sessionStoreContext, subscribe: true })
  public session!: SessionStore;

  /** The community this page is part of; a page outside any one community has none. */
  declare public slug?: string;

  /** The page itself, for someone who may see it. */
  protected abstract content(): TemplateResult;

  public override render(): TemplateResult {
    if (this.slug !== undefined && !this.session?.can("read", "community", this.slug)) {
      return html`<cofy-problem-details .problem=${NO_ACCESS}></cofy-problem-details>`;
    }
    return this.content();
  }

  /** This page's trail. Recomputed after every render, so it may read stores directly. */
  protected abstract crumbs(): Crumb[];

  /** Translate out of the application's own namespace. */
  protected override t(key: string, options?: TOptions): string {
    return super.t(key, { ns: APP_NAMESPACE, ...options });
  }

  public override updated(): void {
    this.trail?.set(this.crumbs());
  }
}
