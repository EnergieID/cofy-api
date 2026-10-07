import { consume, provide } from "@lit/context";
import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { GrantInfo, GrantStore, ProblemError } from "@cofy/frontend-sdk";

import "@awesome.me/webawesome/dist/components/badge/badge.js";
import "@awesome.me/webawesome/dist/components/button/button.js";
import "@awesome.me/webawesome/dist/components/skeleton/skeleton.js";
import "@awesome.me/webawesome/dist/components/scroller/scroller.js";

import { CofyElement } from "../../cofy-element.js";
import { communitySlugContext, grantStoreContext } from "../../context.js";
import { tableStyles } from "../../theme/table.js";
import { utilityStyles } from "../../theme/utility-styles.js";
import "../layout/cofy-heading.js";
import "../cofy-problem-details.js";
import "./cofy-grant-dialog.js";

/** Who has access to a community: each grant with its role and whether its person has logged in since, and its revoke. */
@customElement("cofy-grant-list")
export class CofyGrantList extends CofyElement {
  public static override styles = [
    tableStyles,
    utilityStyles,
    css`
      :host {
        display: block;
      }
      th.actions,
      td.actions {
        inline-size: 1%;
        white-space: nowrap;
        text-align: end;
      }
    `,
  ];

  @consume({ context: grantStoreContext, subscribe: true })
  @state()
  public store!: GrantStore;

  // Provided, so the dialog saves to this community.
  @provide({ context: communitySlugContext })
  @property({ type: String })
  public slug = "";

  @state() private adding = false;
  @state() private revoking = false;
  @state() private revokeError: ProblemError | null = null;

  public override willUpdate(changed: Map<string, unknown>): void {
    if ((changed.has("slug") || changed.has("store")) && this.slug !== "") void this.store?.ensure(this.slug);
  }

  public override render(): TemplateResult | typeof nothing {
    if (this.store === undefined) return nothing;

    const grants = this.store.list(this.slug);

    if (this.store.error != null) return html`<cofy-problem-details .problem=${this.store.error}></cofy-problem-details>`;
    if (grants === undefined) {
      return html`<div class="wa-stack">
        ${Array.from({ length: 3 }, () => html`<wa-skeleton></wa-skeleton>`)}
      </div>`;
    }

    return html`
      <div class="wa-stack">
        <cofy-heading>
          <span slot="title">${this.t("grantList.title")}</span>
          <span slot="description">${this.t("grantList.description")}</span>
          <wa-button
            slot="actions"
            variant="brand"
            @click=${(): void => {
              this.adding = true;
            }}
          >
            ${this.t("grantList.add")}
          </wa-button>
        </cofy-heading>

        ${this.revokeError === null
          ? nothing
          : html`<cofy-problem-details .problem=${this.revokeError}></cofy-problem-details>`}

        <wa-scroller>
          <table>
            <thead>
              <tr>
                <th scope="col">${this.t("grantList.columns.email")}</th>
                <th scope="col">${this.t("grantList.columns.role")}</th>
                <th scope="col">${this.t("grantList.columns.status")}</th>
                <th scope="col" class="actions"><span class="wa-visually-hidden">${this.t("grantList.columns.actions")}</span></th>
              </tr>
            </thead>
            <tbody>
              ${grants.length === 0
                ? html`<tr class="empty">
                    <td class="secondary" colspan="4">${this.t("grantList.empty")}</td>
                  </tr>`
                : grants.map((grant): TemplateResult => this.row(grant))}
            </tbody>
          </table>
        </wa-scroller>
      </div>

      <cofy-grant-dialog
        .open=${this.adding}
        @grant-saved=${(): void => {
          this.adding = false;
        }}
        @dialog-closed=${(): void => {
          this.adding = false;
        }}
      ></cofy-grant-dialog>
    `;
  }

  private row(grant: GrantInfo): TemplateResult {
    return html`
      <tr data-key=${grant.email}>
        <td>${grant.email}</td>
        <td>${this.t(`roles.${grant.role}`)}</td>
        <td>
          <wa-badge variant=${grant.bound ? "success" : "neutral"} appearance="outlined">
            ${grant.bound ? this.t("grantList.bound") : this.t("grantList.invited")}
          </wa-badge>
        </td>
        <td class="actions">
          <wa-button appearance="plain" size="small" ?disabled=${this.revoking} @click=${(): void => void this.revoke(grant)}>
            ${this.revoking ? this.t("grantList.revoking") : this.t("grantList.revoke")}
          </wa-button>
        </td>
      </tr>
    `;
  }

  private async revoke(grant: GrantInfo): Promise<void> {
    if (!window.confirm(this.t("grantList.revokeConfirm", { email: grant.email }))) return;

    this.revoking = true;
    this.revokeError = null;
    try {
      await this.store.remove(this.slug, grant.email);
    } catch (error) {
      this.revokeError = error as ProblemError;
    } finally {
      this.revoking = false;
    }
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-grant-list": CofyGrantList;
  }
}
