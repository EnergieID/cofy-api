import { html } from "lit";
import type { TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";
import { ifDefined } from "lit/directives/if-defined.js";
import { repeat } from "lit/directives/repeat.js";

import "@awesome.me/webawesome/dist/components/option/option.js";
import "@awesome.me/webawesome/dist/components/select/select.js";
import "./cofy-field-shell.js";

import { deref } from "../../schema-ref.js";
import { fieldLabel, primitiveText } from "./field-shell.js";
import { CofyFormField } from "./form-field.js";
import { issuesAt } from "./issues.js";

/** An `enum` field, rendered as a `wa-select`. */
@customElement("cofy-enum-form")
export class CofyEnumForm extends CofyFormField {
  public override render(): TemplateResult {
    const node = deref(this.schema, this.root);
    const description = typeof node["description"] === "string" ? node["description"] : undefined;
    const values = Array.isArray(node["enum"]) ? (node["enum"] as unknown[]) : [];

    return html`
      <cofy-field-shell data-pointer=${this.pointer} .issues=${issuesAt(this.issues, this.pointer)}>
        <wa-select
          label=${fieldLabel(node, this.pointer)}
          hint=${ifDefined(description)}
          .value=${primitiveText(this.value)}
          lang=${this.i18n?.resolvedLanguage ?? "en"}
          ?required=${this.required}
          @change=${(event: Event): void => this.onChange(event, values)}
        >
          ${repeat(
            values,
            (value) => primitiveText(value),
            (value) => html`<wa-option value=${primitiveText(value)}>${primitiveText(value)}</wa-option>`,
          )}
        </wa-select>
      </cofy-field-shell>
    `;
  }

  private onChange(event: Event, values: unknown[]): void {
    const raw = (event.target as HTMLElement & { value?: string }).value ?? "";
    const value = values.find((candidate) => primitiveText(candidate) === raw) ?? raw;
    this.dispatchEvent(
      new CustomEvent("field-change", { bubbles: true, composed: true, detail: { pointer: this.pointer, value } }),
    );
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-enum-form": CofyEnumForm;
  }
}
