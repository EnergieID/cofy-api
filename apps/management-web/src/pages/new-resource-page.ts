import { css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { Crumb } from "@cofy/web-components";

import { nativeStyles } from "@cofy/web-components";
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

  @property({ type: String }) public override slug = "";

  protected override crumbs(): Crumb[] {
    const community = this.cofy?.communities.get(this.slug);
    return [
      { label: community?.title ?? this.slug, href: this.routes.hashFor("resources", { slug: this.slug }) },
      { label: this.t("newResource.crumb") },
    ];
  }

  protected override content(): TemplateResult {
    return html`
      <section>
        <cofy-resource-create
          .slug=${this.slug}
          @resource-created=${(event: CustomEvent<{ slug: string; name: string }>): void =>
            this.routes.navigate("resource", { slug: event.detail.slug, name: event.detail.name })}
          @create-cancelled=${(): void => this.routes.navigate("resources", { slug: this.slug })}
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
