import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property } from "lit/decorators.js";

import { CofyElement } from "../../cofy-element.js";
import { nativeStyles } from "../../theme/native-styles.js";
import { utilityStyles } from "../../theme/utility-styles.js";

/** The one thing every kind of "issue" this shell shows actually needs - a message to print. */
export interface FieldShellIssue {
  message: string;
}

/**
 * Wraps a field's own control (slotted in) with its label above and its errors below - a
 * caller mounts this the same way as any other element, `data-pointer` and all, rather than
 * calling a function that hands back markup to splice in.
 *
 * `label` is left empty by a control that already carries its own (every Web Awesome form
 * control takes one as an attribute) - only a control with no such attribute of its own (a
 * `wa-accordion`, a `wa-card`, a bare `wa-select`-less picker) passes one here instead. Styled
 * with `wa-form-control-label`, the same utility class (and tokens) Web Awesome's own controls
 * use for their label, rather than a second copy of those three declarations.
 *
 * `description` sits after the slotted control and before the issues list - a container (an
 * object's card, a list's accordion, a union's card) has no single control of its own to carry a
 * `hint` attribute the way a leaf's `wa-input`/`wa-select` does, so this is the one place it can
 * show its own schema's `description` at all.
 *
 * `issues` only needs a `message` to print, not a full `ValidationIssue` - a YAML editor's own
 * syntax errors (plain strings) map onto the same shape (`{ message }`) as a caller's schema
 * issues, so both wrap in exactly this one element.
 */
@customElement("cofy-field-shell")
export class CofyFieldShell extends CofyElement {
  public static override styles = [
    nativeStyles,
    utilityStyles,
    css`
      :host {
        display: block;
      }
      .cofy-field-issues {
        padding-inline-start: var(--wa-space-m);
        color: var(--wa-color-danger-fill-loud);
        font-size: var(--wa-font-size-s);
      }
    `,
  ];

  @property({ type: String }) public label = "";
  @property({ type: String }) public description = "";
  @property({ attribute: false }) public issues: readonly FieldShellIssue[] = [];

  public override render(): TemplateResult {
    return html`
      <div class="wa-stack wa-gap-xs">
        ${this.label === ""
          ? nothing
          : html`
          <div class="wa-split">
            <label>${this.label}</label>
            <slot name="actions"></slot>
          </div>`}
        <slot></slot>
        ${this.description === ""
          ? nothing
          : html`<div class="wa-color-text-quiet wa-caption-s">${this.description}</div>`}
        ${this.issues.length === 0
          ? nothing
          : html`<ul class="cofy-field-issues">
              ${this.issues.map((issue) => html`<li>${issue.message}</li>`)}
            </ul>`}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-field-shell": CofyFieldShell;
  }
}
