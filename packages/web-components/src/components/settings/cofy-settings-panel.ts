import { css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement, state } from "lit/decorators.js";

import "@awesome.me/webawesome/dist/components/button/button.js";
import "@awesome.me/webawesome/dist/components/drawer/drawer.js";
import "@awesome.me/webawesome/dist/components/icon/icon.js";
import "@awesome.me/webawesome/dist/components/tooltip/tooltip.js";
import "../../icons.js";

import { CofyElement } from "../../cofy-element.js";
import "./cofy-locale-picker.js";
import "./cofy-theme-picker.js";
import { nativeStyles } from "../../theme/native-styles.js";
import { layoutStyles } from "../../theme/layout-styles.js";

/**
 * The console's global settings, behind one header action.
 *
 * Appearance and language are as global as this console gets, so they live behind one control
 * in the header rather than as two, and the drawer leaves room for whatever comes next without
 * another icon.
 *
 * The drawer opens through `<dialog>` and the top layer, so it is not affected by the layout
 * or stacking context of the header it is nested in, and it brings its own focus trap, inert
 * background and focus return.
 */
@customElement("cofy-settings-panel")
export class CofySettingsPanel extends CofyElement {
  public static override styles = [
    nativeStyles,
    layoutStyles,
    css`
    :host {
      display: contents;
    }
  `];

  @state() private open = false;

  public override render(): TemplateResult {
    const label = this.t("settings.open", { defaultValue: "Settings" });

    return html`
      <wa-button id="settings-trigger" appearance="plain" label=${label} @click=${(): void => this.toggle()}>
        <wa-icon name="gear" library="cofy"></wa-icon>
      </wa-button>
      <wa-tooltip for="settings-trigger">${label}</wa-tooltip>

      <wa-drawer
        placement="end"
        label=${label}
        lang=${this.i18n?.resolvedLanguage ?? "en"}
        ?open=${this.open}
        @wa-after-hide=${(): void => {
          this.open = false;
        }}
      >
        <div class="wa-stack">
          <cofy-theme-picker></cofy-theme-picker>
          <cofy-locale-picker></cofy-locale-picker>
        </div>
      </wa-drawer>
    `;
  }

  private toggle(): void {
    this.open = !this.open;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-settings-panel": CofySettingsPanel;
  }
}
