import { consume } from "@lit/context";
import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { repeat } from "lit/directives/repeat.js";
import type { ProblemError, Role } from "@cofy/frontend-sdk";

import "@awesome.me/webawesome/dist/components/button/button.js";
import "@awesome.me/webawesome/dist/components/dialog/dialog.js";
import "@awesome.me/webawesome/dist/components/input/input.js";
import "@awesome.me/webawesome/dist/components/option/option.js";
import "@awesome.me/webawesome/dist/components/select/select.js";
import "../cofy-problem-details.js";

import { CofyElement } from "../../cofy-element.js";
import { communitySlugContext } from "../../context.js";
import { utilityStyles } from "../../theme/utility-styles.js";

/** The roles a person can be granted. */
export const ROLES: readonly Role[] = ["community_admin"];

/**
 * Grants a role on the community to a person, by email.
 *
 * Opened and closed by its host through `open`: it reports `grant-saved` with the email once
 * stored, and `dialog-closed` when dismissed without saving.
 */
@customElement("cofy-grant-dialog")
export class CofyGrantDialog extends CofyElement {
  public static override styles = [
    utilityStyles,
    css`
      :host {
        display: contents;
      }
    `,
  ];

  @consume({ context: communitySlugContext, subscribe: true })
  @state()
  public slug = "";

  @property({ type: Boolean }) public open = false;

  @state() private email = "";
  @state() private chosenRole: Role = ROLES[0]!;
  @state() private saving = false;
  @state() private error: ProblemError | null = null;

  public override willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("open") && this.open) {
      this.email = "";
      this.chosenRole = ROLES[0]!;
      this.error = null;
    }
  }

  public override render(): TemplateResult {
    return html`
      <wa-dialog label=${this.t("grantDialog.title")} ?open=${this.open} @wa-hide=${(event: Event): void => this.onHide(event)}>
        <div class="wa-stack">
          ${this.error === null ? nothing : html`<cofy-problem-details .problem=${this.error}></cofy-problem-details>`}
          <wa-input
            type="email"
            label=${this.t("grantDialog.email")}
            hint=${this.t("grantDialog.emailHint")}
            required
            .value=${this.email}
            @input=${(event: Event): void => {
              this.email = this.inputValue(event);
            }}
          ></wa-input>
          <wa-select
            label=${this.t("grantDialog.role")}
            .value=${this.chosenRole}
            @change=${(event: Event): void => {
              this.chosenRole = this.inputValue(event) as Role;
            }}
          >
            ${repeat(
              ROLES,
              (role) => role,
              (role): TemplateResult => html`<wa-option value=${role}>${this.t(`roles.${role}`)}</wa-option>`,
            )}
          </wa-select>
        </div>
        <wa-button slot="footer" appearance="plain" @click=${(): void => this.close()}>
          ${this.t("grantDialog.cancel")}
        </wa-button>
        <wa-button
          slot="footer"
          variant="brand"
          ?disabled=${this.email === "" || this.saving}
          @click=${(): void => void this.save()}
        >
          ${this.saving ? this.t("grantDialog.saving") : this.t("grantDialog.save")}
        </wa-button>
      </wa-dialog>
    `;
  }

  private inputValue(event: Event): string {
    return (event.target as HTMLElement & { value?: string }).value ?? "";
  }

  private async save(): Promise<void> {
    const cofy = this.cofy;
    if (cofy === undefined) return;

    this.saving = true;
    this.error = null;
    try {
      const saved = await cofy.grants.create(this.slug, { email: this.email, role: this.chosenRole });
      this.dispatchEvent(new CustomEvent("grant-saved", { detail: { email: saved.email }, bubbles: true, composed: true }));
    } catch (error) {
      this.error = error as ProblemError;
    } finally {
      this.saving = false;
    }
  }

  /** The dialog closing itself - Escape, its close button - rather than a nested element hiding. */
  private onHide(event: Event): void {
    if (event.target !== event.currentTarget) return;
    this.close();
  }

  private close(): void {
    this.dispatchEvent(new CustomEvent("dialog-closed", { bubbles: true, composed: true }));
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-grant-dialog": CofyGrantDialog;
  }
}
