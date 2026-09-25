import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property } from "lit/decorators.js";
import { repeat } from "lit/directives/repeat.js";

import "@awesome.me/webawesome/dist/components/option/option.js";
import "@awesome.me/webawesome/dist/components/select/select.js";

import { CofyElement } from "../../cofy-element.js";

/**
 * Chooses the language for the whole page.
 *
 * A select rather than radio buttons: the list of languages grows with the deployment, and a
 * European product will not stop at two.
 */
@customElement("cofy-locale-picker")
export class CofyLocalePicker extends CofyElement {
  public static override styles = css`
    :host {
      display: block;
    }
  `;

  /** The languages this deployment serves. Defaults to whatever i18next was configured with. */
  @property({ attribute: false }) public languages?: readonly string[];

  public override render(): TemplateResult | typeof nothing {
    const languages = this.languages ?? this.configured();
    if (this.i18n === undefined || languages.length < 2) return nothing;

    return html`
      <wa-select
        label=${this.t("settings.language.legend", { defaultValue: "Language" })}
        placeholder=${this.t("settings.language.choose", { defaultValue: "Choose a language" })}
        .value=${this.i18n.resolvedLanguage ?? this.i18n.language}
        lang=${this.i18n.resolvedLanguage ?? "en"}
        @change=${(event: Event): void =>
          this.select((event.target as HTMLElement & { value?: string }).value)}
      >
        ${repeat(
          languages,
          (language) => language,
          (language): TemplateResult => html`<wa-option value=${language}>${this.nameOf(language)}</wa-option>`,
        )}
      </wa-select>
    `;
  }

  /** The language's own name for itself, which is what a reader looking for it expects. */
  private nameOf(language: string): string {
    const names = new Intl.DisplayNames([language], { type: "language" });
    return names.of(language) ?? language;
  }

  private configured(): readonly string[] {
    const supported: unknown = this.i18n?.options.supportedLngs;
    if (!Array.isArray(supported)) return [];
    // i18next appends this sentinel to whatever it was given.
    return supported.filter((language): language is string => typeof language === "string" && language !== "cimode");
  }

  private select(language: string | undefined): void {
    if (language === undefined || language === this.i18n?.resolvedLanguage) return;
    void this.i18n?.changeLanguage(language);
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-locale-picker": CofyLocalePicker;
  }
}
