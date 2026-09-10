import { State, stateProperty } from "@dodona/lit-state";
import type { Crumb } from "@cofy/web-components";

/**
 * The breadcrumb trail, set by whichever page is showing and read by the header.
 *
 * A page knows what it is displaying and when the names it needs have loaded; the header only
 * knows it has a trail to draw. Holding the trail here keeps the two from having to know
 * about each other.
 */
export class CrumbState extends State {
  @stateProperty public crumbs: Crumb[] = [];

  /** Replace the trail, unless it already says the same thing. */
  public set(crumbs: Crumb[]): void {
    if (JSON.stringify(crumbs) === JSON.stringify(this.crumbs)) return;
    this.crumbs = crumbs;
  }

  public clear(): void {
    this.set([]);
  }
}
