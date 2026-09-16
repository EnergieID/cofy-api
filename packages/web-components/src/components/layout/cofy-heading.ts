import { css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";

import { CofyElement } from "../../cofy-element.js";
import { nativeStyles } from "../../theme/native-styles.js";
import { utilityStyles } from "../../theme/utility-styles.js";

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
    utilityStyles,
    css`
      :host {
        display: block;
      }
    `,
  ];

  public override render(): TemplateResult {
    return html`
      <div class="wa-split">
        <div class="wa-stack wa-gap-3xs">
          <h3><slot name="title"></slot></h3>
          <p class="wa-color-text-quiet"><slot name="description"></slot></p>
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
