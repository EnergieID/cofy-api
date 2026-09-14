import { css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";

import { CofyElement } from "../../cofy-element.js";
import { layoutStyles } from "../../theme/layout-styles.js";
import { nativeStyles } from "../../theme/native-styles.js";

/**
 * A section heading: a title, a description beneath it, and optional actions on the far side -
 * the one layout the module and community lists share, so a change to it changes both.
 *
 * `title` and `description` want an element to carry the `slot` attribute - only elements, not
 * bare text, can be assigned to a named slot - so a caller wraps each in a `<span>`. `actions`
 * is left empty by a caller with none, and simply renders nothing.
 */
@customElement("cofy-heading")
export class CofyHeading extends CofyElement {
  public static override styles = [
    nativeStyles,
    layoutStyles,
    css`
      :host {
        display: block;
      }
      p {
        /* Inherited by the slotted text, same as any other CSS property. */
        color: var(--wa-color-text-quiet);
      }
      .text {
        /* wa-stack's own gap reads as two stacked blocks; a title and its description read as
           one. */
        gap: var(--wa-space-3xs);
      }
    `,
  ];

  public override render(): TemplateResult {
    return html`
      <div class="wa-split">
        <div class="wa-stack text">
          <h3><slot name="title"></slot></h3>
          <p><slot name="description"></slot></p>
        </div>
        <slot name="actions"></slot>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-heading": CofyHeading;
  }
}
