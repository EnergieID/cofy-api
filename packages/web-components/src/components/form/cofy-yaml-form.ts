import { css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement, state } from "lit/decorators.js";

import "../editor/cofy-yaml-editor.js";
import "./cofy-field-shell.js";

import { toYaml } from "../../yaml.js";
import type { YamlEditorChange, YamlEditorIssue } from "../editor/cofy-yaml-editor.js";
import { CofyFormField } from "./form-field.js";

/**
 * A schema shape the generic dispatch does not recognize.
 *
 * Edited as YAML rather than guessed at with a control that might write back something the
 * schema never described.
 */
@customElement("cofy-yaml-form")
export class CofyYamlForm extends CofyFormField {
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
    const issues = [...this.ownIssues, ...this.syntaxErrors.map((message) => ({ message }))];

    return html`
      <cofy-field-shell
        data-pointer=${this.pointer}
        label=${this.label}
        description=${this.description}
        .issues=${issues}
      >
        <slot name="actions" slot="actions"></slot>
        <cofy-yaml-editor
          .text=${this.text}
          .issues=${this.subtreeIssues()}
          @yaml-change=${(event: CustomEvent<YamlEditorChange>): void => this.onYamlChange(event)}
        ></cofy-yaml-editor>
      </cofy-field-shell>
    `;
  }

  /**
   * Every validation issue inside this field's own subtree, with pointers made relative to
   * `this.pointer` - `text` is only this subtree's own YAML, not the whole document, so
   * `cofy-yaml-editor` (which resolves a pointer against `text`'s own parsed structure) needs
   * pointers rooted the same way, or it locates nothing and every issue falls back to the very
   * start of the text. None while `bare`, matching `ownIssues` - an ancestor's own boundary
   * already owns showing this field's issues instead.
   */
  private subtreeIssues(): YamlEditorIssue[] {
    if (this.bare) return [];

    const prefix = this.pointer;
    return this.issues
      .filter((issue) => issue.pointer === prefix || issue.pointer.startsWith(`${prefix}/`))
      .map((issue) => ({ pointer: issue.pointer.slice(prefix.length), message: issue.message }));
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
    "cofy-yaml-form": CofyYamlForm;
  }
}
