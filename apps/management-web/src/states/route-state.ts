import { State, stateProperty } from "@dodona/lit-state";
import type { TemplateResult } from "lit";
import { html } from "lit";

import { buildHash, matchRoute, pathFromHash, type RouteParams, type RouteTable } from "../router.js";

/**
 * Where the app is, as observable state.
 *
 * The path is state first and a URL second: the shell renders from {@link path}, and
 * navigating writes the hash so the address bar, the back button and a shared link agree.
 * Pages address routes by name, so no page spells out a path or touches `window.location`.
 *
 * Hash routing rather than paths, so the console works when served from any prefix without
 * the host needing rewrite rules - which also rules out `@lit-labs/router`, whose hash
 * support is a known gap and which needs a `URLPattern` polyfill outside Chromium.
 */
export class RouteState<Name extends string = string> extends State {
  @stateProperty public path = "/";

  private readonly routes: RouteTable<Name>;

  public constructor(routes: RouteTable<Name>) {
    super();
    this.routes = routes;
    this.path = pathFromHash(window.location.hash);
  }

  /** Follow the address bar until {@link stop} is called. */
  public start(): void {
    window.addEventListener("hashchange", this.onHashChange);
  }

  public stop(): void {
    window.removeEventListener("hashchange", this.onHashChange);
  }

  /** The hash addressing *name*, for a link's `href`. */
  public hashFor(name: Name, params: RouteParams = {}): string {
    return buildHash(this.routes[name].path, params);
  }

  /**
   * Go to *name*.
   *
   * The state is set directly rather than waiting for the browser's `hashchange`, which does
   * not fire when the target hash is the one already shown.
   */
  public navigate(name: Name, params: RouteParams = {}): void {
    const hash = this.hashFor(name, params);
    this.path = pathFromHash(hash);
    if (window.location.hash !== hash) window.location.hash = hash;
  }

  /** The page for the current path, or a not-found message when no route claims it. */
  public render(): TemplateResult {
    const match = matchRoute(this.routes, this.path);
    if (match === undefined) return html`<p>No page for <code>${this.path}</code>.</p>`;
    return match.route.render(match.params);
  }

  private readonly onHashChange = (): void => {
    this.path = pathFromHash(window.location.hash);
  };
}
