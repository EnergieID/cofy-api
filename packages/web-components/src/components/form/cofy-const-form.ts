import { html } from "lit";
import type { TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";

import "./cofy-field-shell.js";

import { deref } from "../../schema-ref.js";
import { utilityStyles } from "../../theme/utility-styles.js";
import { fieldLabel, primitiveText } from "./field-shell.js";
import { CofyFormField } from "./form-field.js";
import { issuesAt } from "./issues.js";

/**
 * A `const`-only field, such as the `type` discriminator - fixed by the schema, so it renders
 * as a read-only label rather than an editable control.
 */
@customElement("cofy-const-form")
export class CofyConstForm extends CofyFormField {
  public static override styles = [utilityStyles];

  public override render(): TemplateResult {
    const node = deref(this.schema, this.root);
    return html`
      <cofy-field-shell data-pointer=${this.pointer} .issues=${issuesAt(this.issues, this.pointer)}>
        <span class="wa-color-text-quiet">${fieldLabel(node, this.pointer)}: ${primitiveText(node["const"])}</span>
      </cofy-field-shell>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-const-form": CofyConstForm;
  }
}
