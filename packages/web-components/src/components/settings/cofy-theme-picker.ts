import { consume } from "@lit/context";
import { css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";
import { repeat } from "lit/directives/repeat.js";

import "@awesome.me/webawesome/dist/components/option/option.js";
import "@awesome.me/webawesome/dist/components/select/select.js";

import { CofyElement } from "../../cofy-element.js";
import { themeStateContext } from "../../context.js";
import { COLOR_SCHEMES, type ColorScheme, type ThemeState } from "../../theme/theme-state.js";

/**
 * Chooses the colour scheme for the whole page.
 *
 * A select, matching `cofy-locale-picker`: "System" is a standing choice rather than a
 * one-off reading, and pick it and the console follows the operating system from then on,
 * including a change made while the page is open.
 */
@customElement("cofy-theme-picker")
export class CofyThemePicker extends CofyElement {
  public static override styles = css`
    :host {
      display: block;
    }
  `;

  @consume({ context: themeStateContext, subscribe: true })
  public theme!: ThemeState;

  public override render(): TemplateResult {
    return html`
      <wa-select
        label=${this.t("settings.theme.legend", { defaultValue: "Appearance" })}
        .value=${this.theme?.scheme ?? "system"}
        lang=${this.i18n?.resolvedLanguage ?? "en"}
        @change=${(event: Event): void => this.select((event.target as HTMLElement & { value?: string }).value)}
      >
        ${repeat(
          COLOR_SCHEMES,
          (scheme) => scheme,
          (scheme): TemplateResult => html`
            <wa-option value=${scheme}>${this.t(`settings.theme.names.${scheme}`, { defaultValue: scheme })}</wa-option>
          `,
        )}
      </wa-select>
    `;
  }

  private select(scheme: string | undefined): void {
    if (scheme !== undefined && (COLOR_SCHEMES as readonly string[]).includes(scheme)) {
      this.theme.select(scheme as ColorScheme);
    }
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-theme-picker": CofyThemePicker;
  }
}
