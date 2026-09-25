import { consume } from "@lit/context";
import { css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { CommunityStore, ModuleId, ModuleStore } from "@cofy/frontend-sdk";
import type { Crumb } from "@cofy/web-components";

import { communityStoreContext, moduleStoreContext } from "@cofy/web-components";
import "@cofy/web-components";

import { CofyPage } from "./cofy-page.js";

/** One module, edited as YAML. */
@customElement("cofy-module-page")
export class CofyModulePage extends CofyPage {
  public static override styles = css`
    :host {
      display: block;
    }
  `;

  @consume({ context: communityStoreContext, subscribe: true })
  public communities!: CommunityStore;

  @consume({ context: moduleStoreContext, subscribe: true })
  public modules!: ModuleStore;

  @property({ type: String }) public slug = "";
  @property({ attribute: false }) public moduleId: ModuleId | null = null;

  protected override crumbs(): Crumb[] {
    const community = this.communities?.communities.find((entry) => entry.slug === this.slug);
    const module = this.moduleId === null ? undefined : this.modules?.find(this.slug, this.moduleId);

    return [
      { label: community?.title ?? this.slug, href: this.routes.hashFor("modules", { slug: this.slug }) },
      { label: module?.display_name ?? module?.name ?? this.moduleId?.name ?? "" },
    ];
  }

  public override render(): TemplateResult {
    return html`<cofy-module-editor .slug=${this.slug} .moduleId=${this.moduleId}></cofy-module-editor>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-module-page": CofyModulePage;
  }
}
