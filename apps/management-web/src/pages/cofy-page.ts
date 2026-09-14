import { consume } from "@lit/context";
import { CofyElement } from "@cofy/web-components";
import type { Crumb } from "@cofy/web-components";
import type { TOptions } from "i18next";

import { crumbStateContext, routeStateContext } from "../context.js";
import type { RouteName } from "../routes.js";
import type { CrumbState } from "../states/crumb-state.js";
import type { RouteState } from "../states/route-state.js";
import { APP_NAMESPACE } from "../i18n.js";

/**
 * What every page needs on top of {@link CofyElement}: the route to navigate by and the trail
 * to publish.
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
