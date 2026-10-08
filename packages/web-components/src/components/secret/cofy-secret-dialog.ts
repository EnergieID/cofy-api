import { consume } from "@lit/context";
import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { ProblemError, SecretBody, SecretInfo } from "@cofy/frontend-sdk";

import "@awesome.me/webawesome/dist/components/button/button.js";
import "@awesome.me/webawesome/dist/components/dialog/dialog.js";
import "@awesome.me/webawesome/dist/components/input/input.js";
import "../cofy-problem-details.js";

import { CofyElement } from "../../cofy-element.js";
import { communitySlugContext } from "../../context.js";
import { utilityStyles } from "../../theme/utility-styles.js";

/**
 * Creates a secret, or - given `secret` - sets a new value for an existing one.
 *
 * A secret's value is never read back, so changing one always means giving it again. Opened and
 * closed by its host through `open`: it reports `secret-saved` with the secret's name once
 * stored, and `dialog-closed` when dismissed without saving.
 */
@customElement("cofy-secret-dialog")
export class CofySecretDialog extends CofyElement {
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
  /** The secret to set a new value for, or `null` to create one. */
  @property({ attribute: false }) public secret: SecretInfo | null = null;

  @state() private name = "";
  @state() private description = "";
  @state() private value = "";
  @state() private saving = false;
  @state() private error: ProblemError | null = null;

  public override willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("open") && this.open) {
      this.name = this.secret?.name ?? "";
      this.description = this.secret?.description ?? "";
      this.value = "";
      this.error = null;
    }
  }

  public override render(): TemplateResult {
    const editing = this.secret !== null;

    return html`
      <wa-dialog
        label=${editing ? this.t("secretDialog.changeTitle", { name: this.secret?.name }) : this.t("secretDialog.title")}
        ?open=${this.open}
        @wa-hide=${(event: Event): void => this.onHide(event)}
      >
        <div class="wa-stack">
          ${this.error === null ? nothing : html`<cofy-problem-details .problem=${this.error}></cofy-problem-details>`}
          ${editing
            ? nothing
            : html`<wa-input
                label=${this.t("secretDialog.name")}
                hint=${this.t("secretDialog.nameHint")}
                required
                .value=${this.name}
                @input=${(event: Event): void => {
                  this.name = this.inputValue(event);
                }}
              ></wa-input>`}
          <wa-input
            label=${this.t("secretDialog.description")}
            .value=${this.description}
            @input=${(event: Event): void => {
              this.description = this.inputValue(event);
            }}
          ></wa-input>
          <wa-input
            type="password"
            password-toggle
            label=${this.t("secretDialog.value")}
            hint=${editing ? this.t("secretDialog.valueHint") : ""}
            required
            .value=${this.value}
            @input=${(event: Event): void => {
              this.value = this.inputValue(event);
            }}
          ></wa-input>
        </div>
        <wa-button slot="footer" appearance="plain" @click=${(): void => this.close()}>
          ${this.t("secretDialog.cancel")}
        </wa-button>
        <wa-button
          slot="footer"
          variant="brand"
          ?disabled=${this.name === "" || this.value === "" || this.saving}
          @click=${(): void => void this.save()}
        >
          ${this.saving ? this.t("secretDialog.saving") : this.t("secretDialog.save")}
        </wa-button>
      </wa-dialog>
    `;
  }

  private inputValue(event: Event): string {
    return (event.target as HTMLElement & { value?: string }).value ?? "";
  }

  private body(): SecretBody {
    return {
      name: this.name,
      description: this.description === "" ? null : this.description,
      value: this.value,
    };
  }

  private async save(): Promise<void> {
    const cofy = this.cofy;
    if (cofy === undefined) return;

    this.saving = true;
    this.error = null;
    try {
      const saved =
        this.secret === null
          ? await cofy.secrets.create(this.slug, this.body())
          : await cofy.secrets.replace(this.slug, this.secret.name, this.body());
      this.dispatchEvent(new CustomEvent("secret-saved", { detail: { name: saved.name }, bubbles: true, composed: true }));
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
    "cofy-secret-dialog": CofySecretDialog;
  }
}
