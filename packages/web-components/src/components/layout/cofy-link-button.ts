import { css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";

import "@awesome.me/webawesome/dist/components/button/button.js";

import { CofyElement } from "../../cofy-element.js";

/**
 * A button that sits inline with surrounding text - none of `<wa-button>`'s own padding or
 * minimum height, just its label - built on a real `<wa-button>` rather than a hand-rolled link,
 * so focus, keyboard activation (Enter/Space - a native `<button>`'s own behavior, not something
 * reimplemented here), and disabled handling all come from the platform for free.
 *
 * Its click is stopped from propagating any further and re-dispatched as this element's own
 * `click` - so a row's own click/toggle handler (an accordion item's summary, say) never also
 * fires because this sits inside it, without every caller having to remember to stop it itself.
 * That re-dispatched event does not bubble: every caller binds directly on its own instance of
 * this element, never on some shared ancestor, so it does not need to - and not bubbling means
 * an inner one (a list nested inside another list's own item, say) can never be mistaken for an
 * outer ancestor's own click the way an accordion's `wa-expand` once was.
 */
@customElement("cofy-link-button")
export class CofyLinkButton extends CofyElement {
  public static override styles = css`
    :host {
      display: contents;
    }
    wa-button::part(button) {
      padding-inline: 0;
      height: auto;
      min-height: 0;
      border: none;
      background: none;
    }
  `;

  public override render(): TemplateResult {
    return html`
      <wa-button appearance="plain" @click=${(event: MouseEvent): void => this.onClick(event)}>
        <slot></slot>
      </wa-button>
    `;
  }

  private onClick(event: MouseEvent): void {
    event.stopPropagation();
    this.dispatchEvent(new Event("click"));
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-link-button": CofyLinkButton;
  }
}
