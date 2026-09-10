import { consume } from "@lit/context";
import { StateController } from "@dodona/lit-state";
import { LitElement } from "lit";
import type { Crumb } from "@cofy/web-components";

import { crumbStateContext, routeStateContext } from "../context.js";
import type { RouteName } from "../routes.js";
import type { CrumbState } from "../states/crumb-state.js";
import type { RouteState } from "../states/route-state.js";

/**
 * What every page needs: the route to navigate by, the trail to publish, and a controller
 * that re-renders it when any state it reads changes.
 *
 * A subclass implements {@link crumbs} and is done; the trail is published after each render,
 * which is late enough that reading a store here cannot race the render that subscribed to
 * it. A subclass overriding `updated` has to call `super.updated()` or its trail stops
 * updating.
 */
export abstract class CofyPage extends LitElement {
  @consume({ context: routeStateContext, subscribe: true })
  public routes!: RouteState<RouteName>;

  @consume({ context: crumbStateContext, subscribe: true })
  public trail!: CrumbState;

  public readonly stateController = new StateController(this);

  /** This page's trail. Recomputed after every render, so it may read stores directly. */
  protected abstract crumbs(): Crumb[];

  public override updated(): void {
    this.trail?.set(this.crumbs());
  }
}
