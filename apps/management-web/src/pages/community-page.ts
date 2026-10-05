import { consume } from "@lit/context";
import { css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { CommunityStore } from "@cofy/frontend-sdk";
import type { Crumb } from "@cofy/web-components";

import { communityStoreContext } from "@cofy/web-components";
import "@cofy/web-components";
import "@awesome.me/webawesome/dist/components/tab/tab.js";
import "@awesome.me/webawesome/dist/components/tab-group/tab-group.js";
import "@awesome.me/webawesome/dist/components/tab-panel/tab-panel.js";

import { CofyPage } from "./cofy-page.js";

/** The tabs of a community, each naming the route it is shown on. */
export const COMMUNITY_TABS = ["modules", "resources", "secrets", "grants"] as const;
export type CommunityTab = (typeof COMMUNITY_TABS)[number];

/**
 * A community: its modules, resources, secrets and who has access, each on a tab of its own.
 *
 * The tab shown is part of the route, so it survives a reload, the back button returns to it,
 * and a page under a tab - a resource's editor - can link back to it.
 */
@customElement("cofy-community-page")
export class CofyCommunityPage extends CofyPage {
  public static override styles = css`
    :host {
      display: block;
    }
  `;

  @consume({ context: communityStoreContext, subscribe: true })
  public communities!: CommunityStore;

  @property({ type: String }) public override slug = "";
  @property({ type: String }) public tab: CommunityTab = "modules";

  protected override crumbs(): Crumb[] {
    return [{ label: this.communityName() }];
  }

  protected override content(): TemplateResult {
    // The tables carry their own titles and toolbars, so a tab adds no chrome of its own.
    return html`
      <wa-tab-group .active=${this.tab} @wa-tab-show=${(event: CustomEvent<{ name: string }>): void => this.show(event)}>
        ${COMMUNITY_TABS.map((tab) => html`<wa-tab panel=${tab}>${this.t(`community.tabs.${tab}`)}</wa-tab>`)}

        <wa-tab-panel name="modules">
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
        </wa-tab-panel>
        <wa-tab-panel name="resources">
          <cofy-resource-list
            .slug=${this.slug}
            @resource-create=${(): void => this.routes.navigate("newResource", { slug: this.slug })}
            @resource-edit=${(event: CustomEvent<{ slug: string; name: string }>): void =>
              this.routes.navigate("resource", { slug: event.detail.slug, name: event.detail.name })}
          ></cofy-resource-list>
        </wa-tab-panel>
        <wa-tab-panel name="secrets">
          <cofy-secret-list .slug=${this.slug}></cofy-secret-list>
        </wa-tab-panel>
        <wa-tab-panel name="grants">
          <cofy-grant-list .slug=${this.slug}></cofy-grant-list>
        </wa-tab-panel>
      </wa-tab-group>
    `;
  }

  /** Follow a tab picked in the group to its own route - the route, not the group, decides what is shown. */
  private show(event: CustomEvent<{ name: string }>): void {
    const tab = COMMUNITY_TABS.find((candidate) => candidate === event.detail.name);
    if (tab === undefined || tab === this.tab) return;
    this.routes.navigate(tab, { slug: this.slug });
  }

  /** Falls back to the slug until the community's name has loaded. */
  private communityName(): string {
    return this.communities?.communities.find((entry) => entry.slug === this.slug)?.title ?? this.slug;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-comunity-page": CofyCommunityPage;
  }
}
