import { consume } from "@lit/context";
import type { CofyStore } from "@cofy/frontend-sdk";
import { StateController } from "@dodona/lit-state";
import { LitElement } from "lit";
import { state } from "lit/decorators.js";
import type { TOptions } from "i18next";

import { cofyStoreContext, i18nContext } from "./context.js";
import type { CofyI18n } from "./i18n/cofy-i18n.js";

/**
 * The base every component in this package builds on.
 *
 * It consumes the store and the translations, and carries a `StateController`, so reading
 * either during render subscribes to it - and, for the store, loads it - and re-renders on a
 * change.
 */
export abstract class CofyElement extends LitElement {
  @consume({ context: i18nContext, subscribe: true })
  public i18n?: CofyI18n;

  // A state, so a component can react to the store being provided or replaced.
  @consume({ context: cofyStoreContext, subscribe: true })
  @state()
  public cofy!: CofyStore;

  public readonly stateController = new StateController(this);

  /**
   * Translate *key*.
   *
   * Before an instance is provided - a component used standalone, or a render that beats the
   * context - this falls back to `defaultValue` and then to the key, so something readable is
   * always on screen.
   */
  protected t(key: string, options?: TOptions): string {
    const fallback = typeof options?.defaultValue === "string" ? options.defaultValue : key;
    return this.i18n?.t(key, options) ?? fallback;
  }
}
