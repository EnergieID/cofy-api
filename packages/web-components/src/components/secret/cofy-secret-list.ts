import { consume, provide } from "@lit/context";
import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { ProblemError, SecretInfo, SecretStore } from "@cofy/frontend-sdk";

import "@awesome.me/webawesome/dist/components/button/button.js";
import "@awesome.me/webawesome/dist/components/skeleton/skeleton.js";
import "@awesome.me/webawesome/dist/components/scroller/scroller.js";

import { CofyElement } from "../../cofy-element.js";
import { communitySlugContext, secretStoreContext } from "../../context.js";
import { tableStyles } from "../../theme/table.js";
import { utilityStyles } from "../../theme/utility-styles.js";
import "../layout/cofy-heading.js";
import "../cofy-problem-details.js";
import "./cofy-secret-dialog.js";

/**
 * The secrets of a community, laid out like `cofy-resource-list`: a row opens its secret - to
 * give it a new value, since a secret's value is only ever written - and carries its own delete.
 */
@customElement("cofy-secret-list")
export class CofySecretList extends CofyElement {
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

  @consume({ context: secretStoreContext, subscribe: true })
  @state()
  public store!: SecretStore;

  // Provided, so the dialog saves to this community.
  @provide({ context: communitySlugContext })
  @property({ type: String })
  public slug = "";

  /** The secret the dialog is open for: `null` to add one, `undefined` while it is closed. */
  @state() private editing: SecretInfo | null | undefined = undefined;
  @state() private deleting = false;
  @state() private deleteError: ProblemError | null = null;

  public override willUpdate(changed: Map<string, unknown>): void {
    if ((changed.has("slug") || changed.has("store")) && this.slug !== "") void this.store?.ensure(this.slug);
  }

  public override render(): TemplateResult | typeof nothing {
    if (this.store === undefined) return nothing;

    const secrets = this.store.list(this.slug);

    if (this.store.error != null) return html`<cofy-problem-details .problem=${this.store.error}></cofy-problem-details>`;
    if (secrets === undefined) {
      return html`<div class="wa-stack">
        ${Array.from({ length: 3 }, () => html`<wa-skeleton></wa-skeleton>`)}
      </div>`;
    }

    return html`
      <div class="wa-stack">
        <cofy-heading>
          <span slot="title">${this.t("secretList.title")}</span>
          <span slot="description">${this.t("secretList.description")}</span>
          <wa-button
            slot="actions"
            variant="brand"
            @click=${(): void => {
              this.editing = null;
            }}
          >
            ${this.t("secretList.add")}
          </wa-button>
        </cofy-heading>

        ${this.deleteError === null
          ? nothing
          : html`<cofy-problem-details .problem=${this.deleteError}></cofy-problem-details>`}

        <wa-scroller>
          <table>
            <thead>
              <tr>
                <th scope="col">${this.t("secretList.columns.secret")}</th>
                <th scope="col">${this.t("secretList.columns.description")}</th>
                <th scope="col" class="actions"><span class="wa-visually-hidden">${this.t("secretList.columns.actions")}</span></th>
              </tr>
            </thead>
            <tbody>
              ${secrets.length === 0
                ? html`<tr class="empty">
                    <td class="secondary" colspan="3">${this.t("secretList.empty")}</td>
                  </tr>`
                : secrets.map((secret): TemplateResult => this.row(secret))}
            </tbody>
          </table>
        </wa-scroller>
      </div>

      <cofy-secret-dialog
        .open=${this.editing !== undefined}
        .secret=${this.editing ?? null}
        @secret-saved=${(): void => {
          this.editing = undefined;
        }}
        @dialog-closed=${(): void => {
          this.editing = undefined;
        }}
      ></cofy-secret-dialog>
    `;
  }

  /** A row opens its secret; the button in it deletes. Keyboard handling as in `cofy-module-list`. */
  private row(secret: SecretInfo): TemplateResult {
    return html`
      <tr
        data-key=${secret.name}
        tabindex="0"
        @click=${(): void => this.open(secret)}
        @keydown=${(event: KeyboardEvent): void => this.onKeydown(event, secret)}
      >
        <td>${secret.name}</td>
        <td class="secondary">${secret.description ?? ""}</td>
        <td class="actions">
          <wa-button
            appearance="plain"
            size="small"
            ?disabled=${this.deleting}
            @click=${(event: MouseEvent): void => {
              // Without this the row's own handler would also fire and open the secret.
              event.stopPropagation();
              void this.deleteSecret(secret);
            }}
          >
            ${this.deleting ? this.t("secretList.deleting") : this.t("secretList.delete")}
          </wa-button>
        </td>
      </tr>
    `;
  }

  private onKeydown(event: KeyboardEvent, secret: SecretInfo): void {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    this.open(secret);
  }

  private open(secret: SecretInfo): void {
    this.editing = secret;
  }

  /** Delete one secret, after asking. One still referenced is refused, and the server says by what. */
  private async deleteSecret(secret: SecretInfo): Promise<void> {
    if (!window.confirm(this.t("secretList.deleteConfirm", { name: secret.name }))) return;

    this.deleting = true;
    this.deleteError = null;
    try {
      await this.store.remove(this.slug, secret.name);
    } catch (error) {
      this.deleteError = error as ProblemError;
    } finally {
      this.deleting = false;
    }
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-secret-list": CofySecretList;
  }
}
