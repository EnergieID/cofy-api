import { ContextProvider } from "@lit/context";
import { beforeEach, describe, expect, it } from "vitest";
import { ApiClient, CofyStore, type Me } from "@cofy/frontend-sdk";

import { CofyLocalePicker } from "../../src/components/settings/cofy-locale-picker.js";
import { CofySettingsPanel } from "../../src/components/settings/cofy-settings-panel.js";
import { CofyThemePicker } from "../../src/components/settings/cofy-theme-picker.js";
import { cofyStoreContext, i18nContext } from "../../src/context.js";
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
    // Hidden itself, so a layout's gap doesn't leave room for an element showing nothing.
    expect(element.hidden).toBe(true);
    expect(getComputedStyle(element).display).toBe("none");
  });

  it("names each language in that language, which is how a reader finds theirs", async () => {
    const element = new CofyLocalePicker();
    element.i18n = await testI18n();
    element.languages = ["en", "nl"];
    await mount(element);

    expect(element.hidden).toBe(false);
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

describe("cofy-settings-panel", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  async function panel(me: Me | null): Promise<CofySettingsPanel> {
    // Who is logged in, or the 401 the API answers without anyone.
    const fetchStub = (): Promise<Response> =>
      Promise.resolve(
        new Response(JSON.stringify(me ?? { status: 401 }), {
          status: me === null ? 401 : 200,
          headers: { "content-type": "application/json" },
        }),
      );
    const cofy = new CofyStore(new ApiClient({ fetch: fetchStub, baseUrl: "http://localhost" }));
    await cofy.session.fetch().catch(() => {});
    const host = document.createElement("div");
    new ContextProvider(host, { context: cofyStoreContext, initialValue: cofy });
    new ContextProvider(host, { context: i18nContext, initialValue: await testI18n() });
    document.body.append(host);
    const element = new CofySettingsPanel();
    host.append(element);
    await element.updateComplete;
    return element;
  }

  function texts(element: CofySettingsPanel): string {
    return element.shadowRoot!.querySelector("wa-drawer")!.textContent.replace(/\s+/g, " ");
  }

  it("shows who is logged in and a way to log out, above the appearance and language", async () => {
    const element = await panel({ email: "ann@example.com", name: "Ann", system_admin: false, permissions: [] });

    expect(texts(element)).toContain("Ann");
    expect(texts(element)).toContain("ann@example.com");
    expect(texts(element)).toContain("Log out");
    const order = Array.from(element.shadowRoot!.querySelector("wa-drawer > .wa-stack")!.children).map((child) =>
      child.tagName.toLowerCase(),
    );
    expect(order).toEqual(["div", "wa-button", "wa-divider", "cofy-theme-picker", "cofy-locale-picker"]);
  });

  it("shows only the language and appearance without anyone logged in", async () => {
    const element = await panel(null);

    expect(texts(element)).not.toContain("Log out");
    expect(element.shadowRoot!.querySelectorAll("wa-divider")).toHaveLength(0);
  });
});
