import { State, stateProperty } from "@dodona/lit-state";
import type { i18n, TOptions } from "i18next";

/**
 * i18next as lit-state.
 *
 * Every `CofyElement` already carries a `StateController`, the same one `ThemeState` and
 * `CrumbState` rely on: it re-renders a component whenever a state property read during its
 * last render later changes. Reading `revision` from {@link t} is what plugs an i18next
 * instance into that, so a component reacting to a language change or a namespace finishing
 * loading needs no controller of its own.
 */
export class CofyI18n extends State {
  /** The wrapped i18next instance, for anything not exposed here directly. */
  public readonly instance: i18n;

  // Bumped on every change i18next reports. The value itself carries no meaning - reading it
  // from `t()` is what subscribes a render to it.
  @stateProperty private revision = 0;

  public constructor(instance: i18n) {
    super();
    this.instance = instance;
    instance.on("languageChanged", this.bump);
    instance.on("loaded", this.bump);
  }

  public get language(): string {
    return this.instance.language;
  }

  public get resolvedLanguage(): string | undefined {
    return this.instance.resolvedLanguage;
  }

  public get options(): i18n["options"] {
    return this.instance.options;
  }

  public changeLanguage(language: string): Promise<unknown> {
    return this.instance.changeLanguage(language);
  }

  /** Translate *key*. */
  public t(key: string, options?: TOptions): string {
    void this.revision;
    return this.instance.t(key, options as never) as unknown as string;
  }

  private readonly bump = (): void => {
    this.revision++;
  };
}
