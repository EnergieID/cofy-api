import { consume } from "@lit/context";
import { css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement, state } from "lit/decorators.js";
import { repeat } from "lit/directives/repeat.js";
import type { SecretInfo, SecretRef, SecretStore } from "@cofy/frontend-sdk";

import "@awesome.me/webawesome/dist/components/button/button.js";
import "@awesome.me/webawesome/dist/components/option/option.js";
import "@awesome.me/webawesome/dist/components/select/select.js";
import "./cofy-field-shell.js";
import "../secret/cofy-secret-dialog.js";

import { communitySlugContext, secretStoreContext } from "../../context.js";
import { utilityStyles } from "../../theme/utility-styles.js";
import { CofyFormField } from "./form-field.js";
import { isRecord } from "./schema/ref.js";

/**
 * A credential (an `x-secret` schema): a reference to one of the community's secrets, picked among
 * them, or to a new one created on the spot - the value itself never passes through the form.
 */
@customElement("cofy-secret-form")
export class CofySecretForm extends CofyFormField {
  public static override styles = [
    utilityStyles,
    css`
      :host {
        display: block;
      }
      .picker {
        display: flex;
        align-items: center;
        gap: var(--wa-space-s);
      }
      .picker wa-select {
        flex: 1;
      }
    `,
  ];

  @consume({ context: secretStoreContext, subscribe: true })
  @state()
  public secretStore?: SecretStore;

  @consume({ context: communitySlugContext, subscribe: true })
  @state()
  public slug = "";

  @state() private creating = false;

  public override willUpdate(changed: Map<string, unknown>): void {
    if ((changed.has("slug") || changed.has("secretStore")) && this.slug !== "") {
      void this.secretStore?.ensure(this.slug);
    }
  }

  public override render(): TemplateResult {
    const secrets = this.secretStore?.list(this.slug) ?? [];
    const none = secrets.length === 0;

    return html`
      <cofy-field-shell
        data-pointer=${this.pointer}
        label=${this.bare ? "" : this.required ? `${this.label}*` : this.label}
        description=${this.description}
        .issues=${this.ownIssues}
      >
        <div class="picker">
          <wa-select
            aria-label=${this.label}
            placeholder=${none ? this.t("form.noSecrets") : this.t("form.chooseSecret")}
            .value=${this.chosenName()}
            ?disabled=${none}
            lang=${this.i18n?.resolvedLanguage ?? "en"}
            @change=${(event: Event): void => this.emit((event.target as HTMLElement & { value?: string }).value ?? "")}
          >
            ${repeat(
              secrets,
              (secret) => secret.name,
              (secret) => html`<wa-option value=${secret.name}>${this.optionLabel(secret)}</wa-option>`,
            )}
          </wa-select>
          <wa-button
            appearance="outlined"
            @click=${(): void => {
              this.creating = true;
            }}
          >
            ${this.t("form.newSecret")}
          </wa-button>
        </div>
      </cofy-field-shell>
      <cofy-secret-dialog
        .open=${this.creating}
        @secret-saved=${(event: CustomEvent<{ name: string }>): void => {
          this.creating = false;
          this.emit(event.detail.name);
        }}
        @dialog-closed=${(): void => {
          this.creating = false;
        }}
      ></cofy-secret-dialog>
    `;
  }

  private chosenName(): string {
    return isRecord(this.value) && typeof this.value["name"] === "string" ? this.value["name"] : "";
  }

  private optionLabel(secret: SecretInfo): string {
    return secret.description ? `${secret.name} — ${secret.description}` : secret.name;
  }

  private emit(name: string): void {
    const value: SecretRef = { type: "secret", name };
    this.dispatchEvent(new CustomEvent("field-change", { bubbles: true, composed: true, detail: { pointer: this.pointer, value } }));
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-secret-form": CofySecretForm;
  }
}
