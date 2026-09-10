import { consume } from "@lit/context";
import { StateController } from "@dodona/lit-state";
import { LitElement, css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";
import type { CommunityInfo, CommunityStore } from "@cofy/frontend-sdk";

import "@carbon/web-components/es/components/data-table/index.js";

import { communityStoreContext } from "../context.js";
import "./cofy-problem-details.js";

/**
 * The communities this API will show.
 *
 * The same table pattern as the module list, so the two read alike: title and search in the
 * table's own toolbar, and a row is the affordance for opening it. Selecting one raises
 * `community-selected`; where that leads is the host's business, which is what keeps this
 * usable outside the console's own routing.
 */
@customElement("cofy-community-list")
export class CofyCommunityList extends LitElement {
  public static override styles = css`
    :host {
      display: block;
    }
    cds-table-row {
      cursor: pointer;
    }
    .secondary {
      color: var(--cds-text-secondary);
    }
  `;

  @consume({ context: communityStoreContext, subscribe: true })
  public store!: CommunityStore;

  public readonly stateController = new StateController(this);

  public override connectedCallback(): void {
    super.connectedCallback();
    if (!this.store?.loaded) void this.store?.load();
  }

  public override render(): TemplateResult | typeof nothing {
    if (this.store === undefined) return nothing;

    const { communities, error, loaded, loading } = this.store;

    if (error !== null) return html`<cofy-problem-details .problem=${error}></cofy-problem-details>`;
    if (loading && !loaded) return html`<cds-table-skeleton row-count="3" column-count="3"></cds-table-skeleton>`;

    // Deliberately not `is-sortable`: Carbon sorts by reordering the row elements in the
    // DOM, which moves nodes Lit owns and corrupts its child-part boundaries - the next
    // render then empties the table. Sorting here would have to sort the data instead.
    return html`
      <cds-table>
        <cds-table-header-title slot="title">Communities</cds-table-header-title>
        <cds-table-header-description slot="description">
          Each community is one Cofy configuration.
        </cds-table-header-description>

        <cds-table-toolbar slot="toolbar">
          <cds-table-toolbar-content>
            <cds-table-toolbar-search placeholder="Search communities"></cds-table-toolbar-search>
          </cds-table-toolbar-content>
        </cds-table-toolbar>

        <cds-table-head>
          <cds-table-header-row>
            <cds-table-header-cell>Community</cds-table-header-cell>
            <cds-table-header-cell>Slug</cds-table-header-cell>
            <cds-table-header-cell>Modules</cds-table-header-cell>
          </cds-table-header-row>
        </cds-table-head>
        <cds-table-body>
          ${communities.length === 0
            ? html`<cds-table-row><cds-table-cell class="secondary">No communities are configured.</cds-table-cell></cds-table-row>`
            : communities.map((community): TemplateResult => this.row(community))}
        </cds-table-body>
      </cds-table>
    `;
  }

  private row(community: CommunityInfo): TemplateResult {
    return html`
      <cds-table-row @click=${(): void => this.select(community)}>
        <cds-table-cell>${community.title || community.slug}</cds-table-cell>
        <cds-table-cell class="secondary">${community.slug}</cds-table-cell>
        <cds-table-cell>${community.module_count}</cds-table-cell>
      </cds-table-row>
    `;
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
