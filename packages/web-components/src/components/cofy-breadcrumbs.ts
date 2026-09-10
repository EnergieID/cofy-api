import { LitElement, css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property } from "lit/decorators.js";

import "@carbon/web-components/es/components/breadcrumb/index.js";

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
export class CofyBreadcrumbs extends LitElement {
  public static override styles = css`
    :host {
      display: block;
    }
  `;

  @property({ attribute: false }) public crumbs: Crumb[] = [];

  public override render(): TemplateResult | typeof nothing {
    if (this.crumbs.length === 0) return nothing;

    return html`
      <cds-breadcrumb no-trailing-slash>
        ${this.crumbs.map(
          (crumb): TemplateResult => html`
            <cds-breadcrumb-item>
              ${crumb.href === undefined
                ? html`<cds-breadcrumb-link aria-current="page">${crumb.label}</cds-breadcrumb-link>`
                : html`<cds-breadcrumb-link href=${crumb.href}>${crumb.label}</cds-breadcrumb-link>`}
            </cds-breadcrumb-item>
          `,
        )}
      </cds-breadcrumb>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-breadcrumbs": CofyBreadcrumbs;
  }
}
