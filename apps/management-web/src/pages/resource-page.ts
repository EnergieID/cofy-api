import { consume } from "@lit/context";
import { css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { CommunityStore } from "@cofy/frontend-sdk";
import type { Crumb } from "@cofy/web-components";

import { communityStoreContext } from "@cofy/web-components";
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

  @consume({ context: communityStoreContext, subscribe: true })
  public communities!: CommunityStore;

  @property({ type: String }) public slug = "";
  @property({ type: String }) public name = "";

  protected override crumbs(): Crumb[] {
    const community = this.communities?.communities.find((entry) => entry.slug === this.slug);
    return [
      { label: community?.title ?? this.slug, href: this.routes.hashFor("modules", { slug: this.slug }) },
      { label: this.name },
    ];
  }

  public override render(): TemplateResult {
    return html`<cofy-resource-editor .slug=${this.slug} .name=${this.name}></cofy-resource-editor>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-resource-page": CofyResourcePage;
  }
}
