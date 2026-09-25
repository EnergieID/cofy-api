import { beforeEach, describe, expect, it } from "vitest";

import { CofyLocalePicker } from "../../src/components/settings/cofy-locale-picker.js";
import { CofyThemePicker } from "../../src/components/settings/cofy-theme-picker.js";
import { ThemeState } from "../../src/theme/theme-state.js";
import { testI18n } from "../support/i18n.js";

function memoryStorage(): Pick<Storage, "getItem" | "setItem"> {
  const values = new Map<string, string>();
  return { getItem: (key) => values.get(key) ?? null, setItem: (key, value) => void values.set(key, value) };
}

async function mount<T extends HTMLElement & { updateComplete: Promise<boolean> }>(element: T): Promise<T> {
  document.body.append(element);
  await element.updateComplete;
  return element;
}

describe("cofy-theme-picker", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("offers system, light and dark, named in the reader's language", async () => {
    const element = new CofyThemePicker();
    element.i18n = await testI18n();
    element.theme = new ThemeState({ storage: memoryStorage(), media: null });
    await mount(element);

    const options = Array.from(element.shadowRoot!.querySelectorAll("wa-option"));

    expect(options.map((option) => option.getAttribute("value"))).toEqual(["system", "light", "dark"]);
    expect(options.map((option) => option.textContent.trim())).toEqual(["System", "Light", "Dark"]);
  });

  it("switches the page's scheme when an option is picked", async () => {
    const element = new CofyThemePicker();
    element.i18n = await testI18n();
    element.theme = new ThemeState({ storage: memoryStorage(), media: null });
    element.theme.start();
    await mount(element);

    const select = element.shadowRoot!.querySelector<HTMLElement & { value: string }>("wa-select")!;
    select.value = "dark";
    select.dispatchEvent(new Event("change", { bubbles: true }));

    expect(element.theme.scheme).toBe("dark");
    expect(element.theme.isDark).toBe(true);
    element.theme.stop();
  });

  it("shows the scheme already in effect", async () => {
    const element = new CofyThemePicker();
    element.i18n = await testI18n();
    element.theme = new ThemeState({ storage: memoryStorage(), media: null });
    element.theme.select("light");
    await mount(element);

    expect(element.shadowRoot!.querySelector<HTMLElement & { value: string }>("wa-select")!.value).toBe("light");
  });
});

describe("cofy-locale-picker", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("stays out of the way when there is only one language to pick", async () => {
    const element = new CofyLocalePicker();
    element.i18n = await testI18n();
    await mount(element);

    expect(element.shadowRoot!.querySelector("wa-select")).toBeNull();
  });

  it("names each language in that language, which is how a reader finds theirs", async () => {
    const element = new CofyLocalePicker();
    element.i18n = await testI18n();
    element.languages = ["en", "nl"];
    await mount(element);

    const items = Array.from(element.shadowRoot!.querySelectorAll("wa-option"));

    expect(items.map((item) => item.getAttribute("value"))).toEqual(["en", "nl"]);
    expect(items.map((item) => item.textContent?.trim())).toEqual(["English", "Nederlands"]);
  });

  it("changes the language when one is chosen", async () => {
    const element = new CofyLocalePicker();
    element.i18n = await testI18n("en", ["en", "nl"]);
    await mount(element);
    const changed = new Promise<string>((resolve) => element.i18n!.instance.on("languageChanged", resolve));

    const select = element.shadowRoot!.querySelector<HTMLElement & { value: string }>("wa-select")!;
    select.value = "nl";
    select.dispatchEvent(new Event("change", { bubbles: true }));

    await expect(changed).resolves.toBe("nl");
  });
});
