import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property } from "lit/decorators.js";

import "@awesome.me/webawesome/dist/components/copy-button/copy-button.js";

import { CofyElement } from "../../cofy-element.js";
import { utilityStyles } from "../../theme/utility-styles.js";
import { nativeStyles } from "../../theme/native-styles.js";

/** Where a community's API is served: its address, to open in a new tab, and to copy. */
@customElement("cofy-api-link")
export class CofyApiLink extends CofyElement {
  public static override styles = [
    nativeStyles,
    utilityStyles,
    css`
      :host {
        display: inline-block;
      }
    `,
  ];

  @property({ type: String }) public url = "";

  public override render(): TemplateResult | typeof nothing {
    if (this.url === "") return nothing;

    return html`
      <div class="wa-cluster wa-gap-3xs">
        <a href=${`${this.url}`} target="_blank">${this.url}</a>
        <wa-copy-button
          value=${this.url}
          copy-label=${this.t("apiLink.copy")}
          success-label=${this.t("apiLink.copied")}
          error-label=${this.t("apiLink.copyFailed")}
        ></wa-copy-button>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-api-link": CofyApiLink;
  }
}
