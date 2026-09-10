import { consume } from "@lit/context";
import { css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { CommunityStore } from "@cofy/frontend-sdk";
import type { Crumb } from "@cofy/web-components";

import "@carbon/web-components/es/components/heading/index.js";
import { communityStoreContext } from "@cofy/web-components";
import "@cofy/web-components";

import { CofyPage } from "./cofy-page.js";

/** Add a module to a community. */
@customElement("cofy-new-module-page")
export class CofyNewModulePage extends CofyPage {
  public static override styles = css`
    :host {
      display: block;
    }
    cds-heading {
      display: block;
      margin-block-end: 1.5rem;
    }
  `;

  @consume({ context: communityStoreContext, subscribe: true })
  public communities!: CommunityStore;

  @property({ type: String }) public slug = "";

  protected override crumbs(): Crumb[] {
    const community = this.communities?.communities.find((entry) => entry.slug === this.slug);
    return [
      { label: community?.title ?? this.slug, href: this.routes.hashFor("modules", { slug: this.slug }) },
      { label: "New module" },
    ];
  }

  public override render(): TemplateResult {
    return html`
      <cds-section>
        <cds-heading>Add module</cds-heading>
        <cofy-module-create
          .slug=${this.slug}
          @module-created=${(event: CustomEvent<{ slug: string; id: { type: string; name: string } }>): void =>
            this.routes.navigate("module", {
              slug: event.detail.slug,
              type: event.detail.id.type,
              name: event.detail.id.name,
            })}
          @create-cancelled=${(): void => this.routes.navigate("modules", { slug: this.slug })}
        ></cofy-module-create>
      </cds-section>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-new-module-page": CofyNewModulePage;
  }
}
