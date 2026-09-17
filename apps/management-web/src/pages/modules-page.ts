import { consume } from "@lit/context";
import { css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { CommunityStore } from "@cofy/frontend-sdk";
import type { Crumb } from "@cofy/web-components";

import { communityStoreContext } from "@cofy/web-components";
import "@cofy/web-components";

import { CofyPage } from "./cofy-page.js";

/** The modules configured in one community. */
@customElement("cofy-modules-page")
export class CofyModulesPage extends CofyPage {
  public static override styles = css`
    :host {
      display: block;
    }
  `;

  @consume({ context: communityStoreContext, subscribe: true })
  public communities!: CommunityStore;

  @property({ type: String }) public slug = "";

  protected override crumbs(): Crumb[] {
    return [{ label: this.communityName() }];
  }

  public override render(): TemplateResult {
    // The table carries its own title and toolbar, so the page adds no chrome of its own.
    return html`
      <cofy-module-list
        .slug=${this.slug}
        @module-create=${(): void => this.routes.navigate("newModule", { slug: this.slug })}
        @module-edit=${(event: CustomEvent<{ slug: string; id: { type: string; name: string } }>): void =>
          this.routes.navigate("module", {
            slug: event.detail.slug,
            type: event.detail.id.type,
            name: event.detail.id.name,
          })}
      ></cofy-module-list>
    `;
  }

  /** Falls back to the slug until the community's name has loaded. */
  private communityName(): string {
    return this.communities?.communities.find((entry) => entry.slug === this.slug)?.title ?? this.slug;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-modules-page": CofyModulesPage;
  }
}
