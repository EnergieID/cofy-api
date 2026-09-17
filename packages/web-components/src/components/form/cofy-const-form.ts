import { html } from "lit";
import type { TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";

import "./cofy-field-shell.js";

import { utilityStyles } from "../../theme/utility-styles.js";
import { CofyFormField } from "./form-field.js";
import { primitiveText } from "./schema/summary.js";

/**
 * A `const`-only field, such as the `type` discriminator - fixed by the schema, so it renders
 * as a read-only label rather than an editable control.
 */
@customElement("cofy-const-form")
export class CofyConstForm extends CofyFormField {
  public static override styles = [utilityStyles];

  public override render(): TemplateResult {
    return html`
      <cofy-field-shell data-pointer=${this.pointer} .issues=${this.ownIssues}>
        <span class="wa-color-text-quiet">${this.label}: ${primitiveText(this.schema["const"])}</span>
      </cofy-field-shell>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-const-form": CofyConstForm;
  }
}
