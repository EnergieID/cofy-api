import { css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement, state } from "lit/decorators.js";

import "../editor/cofy-yaml-editor.js";
import "./cofy-field-shell.js";

import { deref } from "../../schema-ref.js";
import { toYaml } from "../../yaml.js";
import type { YamlEditorChange } from "../editor/cofy-yaml-editor.js";
import { fieldLabel } from "./field-shell.js";
import { CofyFormField } from "./form-field.js";
import { issuesAt } from "./issues.js";

/**
 * A schema shape the generic dispatch does not recognize.
 *
 * Edited as YAML rather than guessed at with a control that might write back something the
 * schema never described.
 */
@customElement("cofy-unknown-form")
export class CofyUnknownForm extends CofyFormField {
  public static override styles = [
    css`
      :host {
        display: block;
      }
    `,
  ];

  @state() private text = "";
  @state() private syntaxErrors: string[] = [];

  /** What was last emitted, so an echo of our own edit does not clobber in-progress typing. */
  private lastEmitted: unknown;

  public override willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("value") && this.value !== this.lastEmitted) {
      this.text = toYaml(this.value);
      this.syntaxErrors = [];
    }
  }

  public override render(): TemplateResult {
    const node = deref(this.schema, this.root);
    const issues = [...issuesAt(this.issues, this.pointer), ...this.syntaxErrors.map((message) => ({ message }))];

    return html`
      <cofy-field-shell data-pointer=${this.pointer} label=${fieldLabel(node, this.pointer)} .issues=${issues}>
        <cofy-yaml-editor
          .text=${this.text}
          @yaml-change=${(event: CustomEvent<YamlEditorChange>): void => this.onYamlChange(event)}
        ></cofy-yaml-editor>
      </cofy-field-shell>
    `;
  }

  private onYamlChange(event: CustomEvent<YamlEditorChange>): void {
    const { text, value, syntaxErrors } = event.detail;
    this.text = text;
    this.syntaxErrors = syntaxErrors;
    if (syntaxErrors.length > 0) return;

    this.lastEmitted = value;
    this.dispatchEvent(
      new CustomEvent("field-change", { bubbles: true, composed: true, detail: { pointer: this.pointer, value } }),
    );
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-unknown-form": CofyUnknownForm;
  }
}
