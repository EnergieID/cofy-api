import { beforeEach, describe, expect, it, vi } from "vitest";

import { COMPONENTS_NAMESPACE, createI18n, preferredLanguage } from "../../src/i18n/i18n.js";
import { yamlBackend } from "../../src/i18n/yaml-backend.js";

const FILES: Record<string, string> = {
  "/locales/en/components.yaml": "moduleList:\n  title: Modules\n  add: Add module\n",
  "/locales/en/app.yaml": "title: Cofy management\n",
  // Deliberately partial: `add` is missing, which is what per-key fallback has to cover.
  "/locales/nl/components.yaml": "moduleList:\n  title: Modules NL\n",
  "/locales/nl/app.yaml": "title: Cofy-beheer\n",
};

const fetch = ((url: string) =>
  Promise.resolve(
    url in FILES ? new Response(FILES[url], { status: 200 }) : new Response(null, { status: 404 }),
  )) as unknown as typeof globalThis.fetch;

const backend = (): ReturnType<typeof yamlBackend> => yamlBackend({ fetch });

function memoryStorage(initial?: string): Pick<Storage, "getItem" | "setItem"> {
  const values = new Map<string, string>(initial === undefined ? [] : [["cofy.language", initial]]);
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => void values.set(key, value),
  };
}

describe("createI18n", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("loads the namespaces it was given, this package's included", async () => {
    const i18n = await createI18n({ language: "en", namespaces: ["app"], backend: backend(), storage: null });

    expect(i18n.t("moduleList.title")).toBe("Modules");
    expect(i18n.t("title", { ns: "app" })).toBe("Cofy management");
    expect(i18n.options.ns).toContain(COMPONENTS_NAMESPACE);
  });

  it("falls back key by key, so a half-finished translation is still worth serving", async () => {
    const i18n = await createI18n({
      language: "nl",
      supportedLanguages: ["en", "nl"],
      backend: backend(),
      storage: null,
    });

    expect(i18n.t("moduleList.title")).toBe("Modules NL");
    expect(i18n.t("moduleList.add")).toBe("Add module");
  });

  it("takes resources supplied directly, with no backend at all", async () => {
    // The point of decoupling the two: a caller does not have to fetch anything to use this.
    const i18n = await createI18n({
      language: "en",
      init: { resources: { en: { components: { moduleList: { title: "Modules" } } } } },
      storage: null,
    });

    expect(i18n.t("moduleList.title")).toBe("Modules");
  });

  it("keeps instances apart, so two consoles on a page do not share a language", async () => {
    const one = await createI18n({ language: "en", supportedLanguages: ["en", "nl"], backend: backend(), storage: null });
    const two = await createI18n({ language: "nl", supportedLanguages: ["en", "nl"], backend: backend(), storage: null });

    expect(one.t("moduleList.title")).toBe("Modules");
    expect(two.t("moduleList.title")).toBe("Modules NL");
  });

  it("remembers a language change, so the choice survives a reload", async () => {
    const storage = memoryStorage();
    const i18n = await createI18n({ language: "en", supportedLanguages: ["en", "nl"], backend: backend(), storage });

    await i18n.changeLanguage("nl");

    expect(storage.getItem("cofy.language")).toBe("nl");
    const reloaded = await createI18n({ supportedLanguages: ["en", "nl"], backend: backend(), storage });
    expect(reloaded.resolvedLanguage).toBe("nl");
  });

  it("ignores a remembered language this deployment no longer serves", async () => {
    const i18n = await createI18n({
      supportedLanguages: ["en"],
      backend: backend(),
      storage: memoryStorage("nl"),
    });

    expect(i18n.resolvedLanguage).toBe("en");
  });
});

describe("preferredLanguage", () => {
  it.each([
    [["nl-BE", "en"], ["en", "nl"], "nl"],
    [["fr-FR"], ["en", "nl"], "en"],
    [["nl"], ["en", "nl"], "nl"],
  ])("picks %s out of %s as %s", (browser, supported, expected) => {
    vi.spyOn(globalThis.navigator, "languages", "get").mockReturnValue(browser);

    expect(preferredLanguage(supported)).toBe(expected);
  });
});
