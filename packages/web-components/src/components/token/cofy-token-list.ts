import { provide } from "@lit/context";
import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { ProblemError, TokenInfo } from "@cofy/frontend-sdk";

import "@awesome.me/webawesome/dist/components/badge/badge.js";
import "@awesome.me/webawesome/dist/components/button/button.js";
import "@awesome.me/webawesome/dist/components/format-date/format-date.js";
import "@awesome.me/webawesome/dist/components/skeleton/skeleton.js";
import "@awesome.me/webawesome/dist/components/scroller/scroller.js";

import { CofyElement } from "../../cofy-element.js";
import { communitySlugContext } from "../../context.js";
import { tableStyles } from "../../theme/table.js";
import { utilityStyles } from "../../theme/utility-styles.js";
import "../layout/cofy-heading.js";
import "../cofy-problem-details.js";
import "./cofy-token-dialog.js";

/**
 * The API tokens of a community, laid out like `cofy-secret-list`: a row opens its token - to
 * change its description or expiry, since a key is only ever generated - and carries its own delete.
 */
@customElement("cofy-token-list")
export class CofyTokenList extends CofyElement {
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

  // Provided, so the dialog saves to this community.
  @provide({ context: communitySlugContext })
  @property({ type: String })
  public slug = "";

  /** The token the dialog is open for: `null` to create one, `undefined` while it is closed. */
  @state() private editing: TokenInfo | null | undefined = undefined;
  @state() private deleting = false;
  @state() private deleteError: ProblemError | null = null;

  public override render(): TemplateResult | typeof nothing {
    if (this.cofy === undefined || this.slug === "") return nothing;

    const tokens = this.cofy.tokens.all(this.slug);
    const error = this.cofy.tokens.error(this.slug);
    if (error !== null) return html`<cofy-problem-details .problem=${error}></cofy-problem-details>`;
    if (tokens === undefined) {
      return html`<div class="wa-stack">
        ${Array.from({ length: 3 }, () => html`<wa-skeleton></wa-skeleton>`)}
      </div>`;
    }

    return html`
      <div class="wa-stack">
        <cofy-heading>
          <span slot="title">${this.t("tokenList.title")}</span>
          <span slot="description">${this.t("tokenList.description")}</span>
          <wa-button
            slot="actions"
            variant="brand"
            @click=${(): void => {
              this.editing = null;
            }}
          >
            ${this.t("tokenList.add")}
          </wa-button>
        </cofy-heading>

        ${this.deleteError === null
          ? nothing
          : html`<cofy-problem-details .problem=${this.deleteError}></cofy-problem-details>`}

        <wa-scroller>
          <table>
            <thead>
              <tr>
                <th scope="col">${this.t("tokenList.columns.token")}</th>
                <th scope="col">${this.t("tokenList.columns.description")}</th>
                <th scope="col">${this.t("tokenList.columns.expires")}</th>
                <th scope="col" class="actions"><span class="wa-visually-hidden">${this.t("tokenList.columns.actions")}</span></th>
              </tr>
            </thead>
            <tbody>
              ${tokens.length === 0
                ? html`<tr class="empty">
                    <td class="secondary" colspan="4">${this.t("tokenList.empty")}</td>
                  </tr>`
                : tokens.map((token): TemplateResult => this.row(token))}
            </tbody>
          </table>
        </wa-scroller>
      </div>

      <cofy-token-dialog
        .open=${this.editing !== undefined}
        .token=${this.editing ?? null}
        @token-saved=${(): void => {
          this.editing = undefined;
        }}
        @dialog-closed=${(): void => {
          this.editing = undefined;
        }}
      ></cofy-token-dialog>
    `;
  }

  /** A row opens its token; the button in it deletes. Keyboard handling as in `cofy-module-list`. */
  private row(token: TokenInfo): TemplateResult {
    return html`
      <tr
        data-key=${token.name}
        tabindex="0"
        @click=${(): void => this.open(token)}
        @keydown=${(event: KeyboardEvent): void => this.onKeydown(event, token)}
      >
        <td>${token.name}</td>
        <td class="secondary">${token.description ?? ""}</td>
        <td class="expires">${this.expiry(token)}</td>
        <td class="actions">
          <wa-button
            appearance="plain"
            size="small"
            ?disabled=${this.deleting}
            @click=${(event: MouseEvent): void => {
              // Without this the row's own handler would also fire and open the token.
              event.stopPropagation();
              void this.deleteToken(token);
            }}
          >
            ${this.deleting ? this.t("tokenList.deleting") : this.t("tokenList.delete")}
          </wa-button>
        </td>
      </tr>
    `;
  }

  private expiry(token: TokenInfo): TemplateResult {
    if (token.expires === null || token.expires === undefined) {
      return html`<span class="secondary">${this.t("tokenList.never")}</span>`;
    }
    const date = html`<wa-format-date date=${token.expires} year="numeric" month="short" day="numeric"></wa-format-date>`;
    if (new Date(token.expires) > new Date()) return date;
    return html`<div class="wa-cluster wa-gap-2xs">
      ${date}<wa-badge variant="danger" appearance="outlined">${this.t("tokenList.expired")}</wa-badge>
    </div>`;
  }

  private onKeydown(event: KeyboardEvent, token: TokenInfo): void {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    this.open(token);
  }

  private open(token: TokenInfo): void {
    this.editing = token;
  }

  /** Delete one token, after asking: whatever uses it can no longer reach the API. */
  private async deleteToken(token: TokenInfo): Promise<void> {
    if (!window.confirm(this.t("tokenList.deleteConfirm", { name: token.name }))) return;

    this.deleting = true;
    this.deleteError = null;
    try {
      await this.cofy.tokens.delete(this.slug, token.name);
    } catch (error) {
      this.deleteError = error as ProblemError;
    } finally {
      this.deleting = false;
    }
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-token-list": CofyTokenList;
  }
}
