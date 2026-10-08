import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";
import type { CommunityInfo } from "@cofy/frontend-sdk";

import "@awesome.me/webawesome/dist/components/skeleton/skeleton.js";
import "@awesome.me/webawesome/dist/components/scroller/scroller.js";

import { CofyElement } from "../../cofy-element.js";
import { tableStyles } from "../../theme/table.js";
import { utilityStyles } from "../../theme/utility-styles.js";
import "../layout/cofy-heading.js";
import "../cofy-problem-details.js";
import "./cofy-community-status.js";

/**
 * The communities this API will show.
 *
 * The same table pattern as the module list, so the two read alike, and a row is the
 * affordance for opening one. Selecting a community raises `community-selected`; where that
 * leads is the host's business, which is what keeps this usable outside the console's routing.
 */
@customElement("cofy-community-list")
export class CofyCommunityList extends CofyElement {
  public static override styles = [
    tableStyles,
    utilityStyles,
    css`
      :host {
        display: block;
      }
    `,
  ];

  public override render(): TemplateResult | typeof nothing {
    if (this.cofy === undefined) return nothing;

    const communities = this.cofy.communities.all();
    const error = this.cofy.communities.error();

    if (error !== null) return html`<cofy-problem-details .problem=${error}></cofy-problem-details>`;
    if (communities === undefined) {
      return html`<div class="wa-stack">
        ${Array.from({ length: 4 }, () => html`<wa-skeleton></wa-skeleton>`)}
      </div>`;
    }

    return html`
      <div class="wa-stack">
        <cofy-heading>
          <span slot="title">${this.t("communityList.title")}</span>
          <span slot="description">${this.t("communityList.description")}</span>
        </cofy-heading>

        <wa-scroller>
          <table>
            <thead>
              <tr>
                <th scope="col">${this.t("communityList.columns.community")}</th>
                <th scope="col">${this.t("communityList.columns.slug")}</th>
                <th scope="col">${this.t("communityList.columns.modules")}</th>
                <th scope="col">${this.t("communityList.columns.status")}</th>
              </tr>
            </thead>
            <tbody>
              ${communities.length === 0
                ? html`<tr class="empty">
                    <td class="secondary" colspan="4">${this.t("communityList.empty")}</td>
                  </tr>`
                : communities.map((community): TemplateResult => this.row(community))}
            </tbody>
          </table>
        </wa-scroller>
      </div>
    `;
  }

  /**
   * A row opens its community.
   *
   * `<tr>` is not focusable of its own accord the way a framework's row component is, so the
   * keyboard handling here is what keeps the list usable without a mouse.
   */
  private row(community: CommunityInfo): TemplateResult {
    return html`
      <tr
        data-slug=${community.slug}
        tabindex="0"
        @click=${(): void => this.select(community)}
        @keydown=${(event: KeyboardEvent): void => this.onKeydown(event, community)}
      >
        <td>${community.title || community.slug}</td>
        <td class="secondary">${community.slug}</td>
        <td>${community.module_count}</td>
        <td><cofy-community-status .slug=${community.slug}></cofy-community-status></td>
      </tr>
    `;
  }

  private onKeydown(event: KeyboardEvent, community: CommunityInfo): void {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    this.select(community);
  }

  private select(community: CommunityInfo): void {
    this.dispatchEvent(
      new CustomEvent("community-selected", {
        detail: { slug: community.slug },
        bubbles: true,
        composed: true,
      }),
    );
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-community-list": CofyCommunityList;
  }
}
