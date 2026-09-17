import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property } from "lit/decorators.js";
import { ifDefined } from "lit/directives/if-defined.js";

import { CofyElement } from "../../cofy-element.js";

import "@awesome.me/webawesome/dist/components/breadcrumb/breadcrumb.js";
import "@awesome.me/webawesome/dist/components/breadcrumb-item/breadcrumb-item.js";

/** One step in the trail. Without an `href` it is the page you are on. */
export interface Crumb {
  label: string;
  href?: string;
}

/**
 * Where you are, and the way back.
 *
 * The last crumb is the current page and is never a link. An empty trail renders nothing, so
 * the root page carries no chrome it does not need.
 */
@customElement("cofy-breadcrumbs")
export class CofyBreadcrumbs extends CofyElement {
  public static override styles = css`
    :host {
      display: block;
    }
  `;

  @property({ attribute: false }) public crumbs: Crumb[] = [];

  public override render(): TemplateResult | typeof nothing {
    if (this.crumbs.length === 0) return nothing;

    return html`
      <wa-breadcrumb>
        ${this.crumbs.map((crumb): TemplateResult => {
          // No `href` at all for the current page, rather than an empty one: the component
          // treats *any* string, "" included, as a real link, so `href=""` rendered an <a>
          // whose empty target silently navigated to the page's URL without its hash - which
          // this app's hash router then reads back as "/". Marking it current is on us, since
          // the component only distinguishes link-or-not, not which link is the current page.
          const current = crumb.href === undefined;
          return html`
            <wa-breadcrumb-item href=${ifDefined(crumb.href)} aria-current=${current ? "page" : nothing}>
              ${crumb.label}
            </wa-breadcrumb-item>
          `;
        })}
      </wa-breadcrumb>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-breadcrumbs": CofyBreadcrumbs;
  }
}
