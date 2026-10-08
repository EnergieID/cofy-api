import { css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { Crumb } from "@cofy/web-components";

import "@cofy/web-components";

import { CofyPage } from "./cofy-page.js";

/** One resource, edited in place. */
@customElement("cofy-resource-page")
export class CofyResourcePage extends CofyPage {
  public static override styles = css`
    :host {
      display: block;
    }
  `;

  @property({ type: String }) public override slug = "";
  @property({ type: String }) public name = "";

  protected override crumbs(): Crumb[] {
    const community = this.cofy?.communities.get(this.slug);
    return [
      { label: community?.title ?? this.slug, href: this.routes.hashFor("resources", { slug: this.slug }) },
      { label: this.name },
    ];
  }

  protected override content(): TemplateResult {
    return html`<cofy-resource-editor .slug=${this.slug} .name=${this.name}></cofy-resource-editor>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-resource-page": CofyResourcePage;
  }
}
