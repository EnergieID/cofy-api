import { css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property } from "lit/decorators.js";
import { repeat } from "lit/directives/repeat.js";

import "@awesome.me/webawesome/dist/components/button/button.js";
import "@awesome.me/webawesome/dist/components/dropdown/dropdown.js";
import "@awesome.me/webawesome/dist/components/dropdown-item/dropdown-item.js";
import "@awesome.me/webawesome/dist/components/icon/icon.js";
import "../../icons.js";

import { CofyElement } from "../../cofy-element.js";

/** One entry in a {@link CofyActionMenu}. */
export interface MenuAction {
  id: string;
  label: string;
  run(): void;
}

/** A field's actions, behind a three-dot button - for a field with more than one thing to do to it. */
@customElement("cofy-action-menu")
export class CofyActionMenu extends CofyElement {
  public static override styles = css`
    :host {
      display: inline-block;
    }
  `;

  @property({ attribute: false }) public actions: readonly MenuAction[] = [];

  public override render(): TemplateResult {
    return html`
      <wa-dropdown placement="bottom-end" @wa-select=${(event: CustomEvent<{ item: { value: string } }>): void => this.onSelect(event)}>
        <wa-button slot="trigger" appearance="plain" size="small" title=${this.t("form.actions")}>
          <wa-icon name="dots" library="cofy" label=${this.t("form.actions")}></wa-icon>
        </wa-button>
        ${repeat(
          this.actions,
          (action) => action.id,
          (action) => html`<wa-dropdown-item value=${action.id}>${action.label}</wa-dropdown-item>`,
        )}
      </wa-dropdown>
    `;
  }

  private onSelect(event: CustomEvent<{ item: { value: string } }>): void {
    this.actions.find((action) => action.id === event.detail.item.value)?.run();
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-action-menu": CofyActionMenu;
  }
}
