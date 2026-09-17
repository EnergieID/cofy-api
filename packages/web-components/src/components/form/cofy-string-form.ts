import { html } from "lit";
import type { TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";
import { ifDefined } from "lit/directives/if-defined.js";

import "@awesome.me/webawesome/dist/components/input/input.js";
import "./cofy-field-shell.js";

import { CofyFormField } from "./form-field.js";

/** A plain string field, rendered as a `wa-input`. */
@customElement("cofy-string-form")
export class CofyStringForm extends CofyFormField {
  public override render(): TemplateResult {
    return html`
      <cofy-field-shell data-pointer=${this.pointer} .issues=${this.ownIssues}>
        <wa-input
          label=${this.label}
          hint=${ifDefined(this.description || undefined)}
          .value=${typeof this.value === "string" ? this.value : ""}
          ?required=${this.required}
          @input=${(event: Event): void => this.onInput(event)}
        ></wa-input>
      </cofy-field-shell>
    `;
  }

  private onInput(event: Event): void {
    const value = (event.target as HTMLElement & { value?: string }).value ?? "";
    this.dispatchEvent(
      new CustomEvent("field-change", { bubbles: true, composed: true, detail: { pointer: this.pointer, value } }),
    );
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-string-form": CofyStringForm;
  }
}
