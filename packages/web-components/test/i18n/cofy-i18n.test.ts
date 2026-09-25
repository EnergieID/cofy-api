import { describe, expect, it } from "vitest";
import type { i18n } from "i18next";

import { CofyI18n } from "../../src/i18n/cofy-i18n.js";

/** An i18next stand-in that only has to record who is listening to what, and translate. */
function stubI18n(): i18n & { emit: (event: string) => void } {
  const listeners = new Map<string, Set<() => void>>();
  return {
    t: (key: string) => key,
    on: (event: string, handler: () => void) => {
      (listeners.get(event) ?? listeners.set(event, new Set()).get(event)!).add(handler);
    },
    off: (event: string, handler: () => void) => void listeners.get(event)?.delete(handler),
    emit: (event: string) => listeners.get(event)?.forEach((handler) => handler()),
  } as unknown as i18n & { emit: (event: string) => void };
}

describe("CofyI18n", () => {
  it("delegates translation to the wrapped instance", () => {
    const instance = stubI18n();
    instance.t = ((key: string) => `translated:${key}`) as i18n["t"];

    expect(new CofyI18n(instance).t("greeting")).toBe("translated:greeting");
  });

  // These are what let a `CofyElement` re-render on a language change or a loaded namespace
  // with no controller of its own: it already has a `StateController`, the same one
  // `ThemeState` and `CrumbState` rely on, and `subscribe` is the low-level primitive that
  // drives.
  it("notifies subscribers when the language changes", () => {
    const instance = stubI18n();
    const i18n = new CofyI18n(instance);
    const seen: unknown[] = [];
    i18n.subscribe(() => seen.push(i18n.t("key")));

    instance.emit("languageChanged");

    expect(seen).toEqual(["key"]);
  });

  it("notifies subscribers when a namespace finishes loading, not only on a language change", () => {
    // Namespaces are fetched, so a component that rendered before one loaded needs telling
    // once it has.
    const instance = stubI18n();
    const i18n = new CofyI18n(instance);
    const seen: unknown[] = [];
    i18n.subscribe(() => seen.push(true));

    instance.emit("loaded");

    expect(seen).toEqual([true]);
  });
});
