import { consume } from "@lit/context";
import { css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { CommunityStore } from "@cofy/frontend-sdk";
import type { Crumb } from "@cofy/web-components";

import { communityStoreContext, nativeStyles } from "@cofy/web-components";
import "@cofy/web-components";

import { CofyPage } from "./cofy-page.js";

/** Add a resource to a community. */
@customElement("cofy-new-resource-page")
export class CofyNewResourcePage extends CofyPage {
  public static override styles = [
    nativeStyles,
    css`
      :host {
        display: block;
      }
    `,
  ];

  @consume({ context: communityStoreContext, subscribe: true })
  public communities!: CommunityStore;

  @property({ type: String }) public slug = "";

  protected override crumbs(): Crumb[] {
    const community = this.communities?.communities.find((entry) => entry.slug === this.slug);
    return [
      { label: community?.title ?? this.slug, href: this.routes.hashFor("modules", { slug: this.slug }) },
      { label: this.t("newResource.crumb") },
    ];
  }

  public override render(): TemplateResult {
    return html`
      <section>
        <cofy-resource-create
          .slug=${this.slug}
          @resource-created=${(event: CustomEvent<{ slug: string; name: string }>): void =>
            this.routes.navigate("resource", { slug: event.detail.slug, name: event.detail.name })}
          @create-cancelled=${(): void => this.routes.navigate("modules", { slug: this.slug })}
        ></cofy-resource-create>
      </section>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-new-resource-page": CofyNewResourcePage;
  }
}
