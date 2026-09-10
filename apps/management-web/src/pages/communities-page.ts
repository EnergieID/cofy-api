import { css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";
import type { Crumb } from "@cofy/web-components";

import "@cofy/web-components";

import { CofyPage } from "./cofy-page.js";

/** The root page: pick a community. */
@customElement("cofy-communities-page")
export class CofyCommunitiesPage extends CofyPage {
  public static override styles = css`
    :host {
      display: block;
    }
  `;

  /** The root page is itself the picker, so there is nowhere to point back to. */
  protected override crumbs(): Crumb[] {
    return [];
  }

  public override render(): TemplateResult {
    // The table carries its own title and toolbar, so the page adds no chrome of its own.
    return html`
      <cofy-community-list
        @community-selected=${(event: CustomEvent<{ slug: string }>): void =>
          this.routes.navigate("modules", { slug: event.detail.slug })}
      ></cofy-community-list>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-communities-page": CofyCommunitiesPage;
  }
}
