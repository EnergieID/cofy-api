import { beforeEach, describe, expect, it } from "vitest";
import { AllowedModulesStore, ApiClient, ModuleStore, type ModuleSettings } from "@cofy/frontend-sdk";

import { CofyModuleEditor } from "../../src/components/module/cofy-module-editor.js";
import { testI18n } from "../support/i18n.js";

const stored: ModuleSettings = {
  type: "tariff",
  name: "spot",
  display_name: null,
  description: null,
  source: { type: "entsoe_day_ahead", api_key: "**********", country_code: "BE" },
};

const catalog = [{ type: "tariff", description: "Tariff", schema: { type: "object" } }];

function stubApi(allowedModules: unknown = catalog): ApiClient {
  const fetchStub = (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const request = input instanceof Request ? input : new Request(input, init);
    const path = new URL(request.url).pathname;
    const body = path.endsWith("/allowed-modules") ? allowedModules : [stored];
    return Promise.resolve(
      new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } }),
    );
  };
  return new ApiClient({ fetch: fetchStub, baseUrl: "http://localhost" });
}

async function mount(allowedModules?: unknown): Promise<CofyModuleEditor> {
  const api = stubApi(allowedModules);
  const element = new CofyModuleEditor();
  element.i18n = await testI18n();
  element.moduleStore = new ModuleStore(api);
  element.allowedModules = new AllowedModulesStore(api);
  element.slug = "test";
  element.moduleId = { type: "tariff", name: "spot" };
  document.body.append(element);
  await element.updateComplete;
  await new Promise((resolve) => setTimeout(resolve, 20));
  await element.updateComplete;
  return element;
}

/** What `cofy-module-form` would report after an edit, however it was made (form or YAML). */
function edit(element: CofyModuleEditor, value: ModuleSettings): void {
  element.shadowRoot!
    .querySelector("cofy-module-form")!
    .dispatchEvent(new CustomEvent("module-form-change", { detail: { value }, bubbles: true, composed: true }));
}

/** Save/Discard, scoped to the footer - the heading's own view-toggle is also a `wa-button`. */
function footerButtons(element: CofyModuleEditor): NodeListOf<Element> {
  return element.shadowRoot!.querySelectorAll("footer wa-button");
}

describe("cofy-module-editor", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("shows a fixed title in its heading, with the view toggle beside it as an action", async () => {
    const element = await mount();

    expect(element.shadowRoot!.querySelector('cofy-heading [slot="title"]')?.textContent?.trim()).toBe(
      "Edit module",
    );
    expect(element.shadowRoot!.querySelector('cofy-heading wa-button[slot="actions"]')).not.toBeNull();
  });

  it("toggles the form to YAML from the heading, reflecting the current value without saving", async () => {
    const element = await mount();
    edit(element, { ...stored, display_name: "Spot prices" });
    await element.updateComplete;

    element.shadowRoot!
      .querySelector<HTMLElement>('cofy-heading wa-button[slot="actions"]')!
      .dispatchEvent(new MouseEvent("click"));
    await element.updateComplete;

    const moduleForm = element.shadowRoot!.querySelector("cofy-module-form")!;
    expect(moduleForm.mode).toBe("yaml");
    expect(moduleForm.shadowRoot!.querySelector("cofy-yaml-editor")!.text).toContain("display_name: Spot prices");
  });

  it("hides the type picker once viewing YAML - it is already part of that text", async () => {
    const element = await mount();
    const moduleForm = element.shadowRoot!.querySelector("cofy-module-form")!;
    expect(moduleForm.shadowRoot!.querySelector("wa-select")).not.toBeNull();

    element.shadowRoot!
      .querySelector<HTMLElement>('cofy-heading wa-button[slot="actions"]')!
      .dispatchEvent(new MouseEvent("click"));
    await element.updateComplete;

    expect(moduleForm.shadowRoot!.querySelector("wa-select")).toBeNull();
  });

  it("passes the stored module's value down to the form", async () => {
    const element = await mount();

    const value = element.shadowRoot!.querySelector("cofy-module-form")!.value as ModuleSettings;

    expect(value).toEqual(stored);
  });

  it("puts the original value back into the form on discard", async () => {
    const element = await mount();

    edit(element, { ...stored, display_name: "Spot prices" });
    await element.updateComplete;
    expect((element.shadowRoot!.querySelector("cofy-module-form")!.value as ModuleSettings).display_name).toBe(
      "Spot prices",
    );

    footerButtons(element)[1]!.dispatchEvent(new MouseEvent("click"));
    await element.updateComplete;

    expect(element.shadowRoot!.querySelector("cofy-module-form")!.value).toEqual(stored);
  });

  it("enables the actions only once there is something to save", async () => {
    const element = await mount();

    expect(footerButtons(element)[0]!.hasAttribute("disabled")).toBe(true);
    expect(footerButtons(element)[1]!.hasAttribute("disabled")).toBe(true);

    edit(element, { ...stored, display_name: "Spot prices" });
    await element.updateComplete;

    expect(footerButtons(element)[0]!.hasAttribute("disabled")).toBe(false);
    expect(footerButtons(element)[1]!.hasAttribute("disabled")).toBe(false);
  });

  it("blocks save when the edit changes the module's identity", async () => {
    const element = await mount();

    edit(element, { ...stored, name: "renamed" });
    await element.updateComplete;

    expect(footerButtons(element)[0]!.hasAttribute("disabled")).toBe(true);
  });

  it("shows validation issues as a plain badge, not a clickable list", async () => {
    const brokenCatalog = [
      { type: "tariff", description: "Tariff", schema: { type: "object", required: ["missing"] } },
    ];
    const element = await mount(brokenCatalog);

    const badge = element.shadowRoot!.querySelector("wa-badge");
    expect(badge).not.toBeNull();
    expect(badge!.getAttribute("variant")).toBe("danger");
    expect(badge!.textContent).toMatch(/blocks? saving/);
    expect(element.shadowRoot!.querySelector("ul.issues")).toBeNull();
  });
});
