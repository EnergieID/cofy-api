import { html } from "lit";
import type { TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";
import { ifDefined } from "lit/directives/if-defined.js";

import "@awesome.me/webawesome/dist/components/checkbox/checkbox.js";
import "./cofy-field-shell.js";

import { CofyFormField } from "./form-field.js";

/** A boolean field, rendered as a `wa-checkbox` (its label lives in the default slot, not an attribute). */
@customElement("cofy-boolean-form")
export class CofyBooleanForm extends CofyFormField {
  public override render(): TemplateResult {
    return html`
      <cofy-field-shell data-pointer=${this.pointer} .issues=${this.ownIssues}>
        <wa-checkbox
          hint=${ifDefined(this.description || undefined)}
          ?checked=${Boolean(this.value)}
          ?required=${this.required}
          @change=${(event: Event): void => this.onChange(event)}
        >
          ${this.label}
        </wa-checkbox>
      </cofy-field-shell>
    `;
  }

  private onChange(event: Event): void {
    const value = (event.target as HTMLElement & { checked?: boolean }).checked ?? false;
    this.dispatchEvent(
      new CustomEvent("field-change", { bubbles: true, composed: true, detail: { pointer: this.pointer, value } }),
    );
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-boolean-form": CofyBooleanForm;
  }
}
