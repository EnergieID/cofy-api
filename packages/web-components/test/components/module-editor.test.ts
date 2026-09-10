import { beforeEach, describe, expect, it } from "vitest";
import { AllowedModulesStore, ApiClient, ModuleStore, type ModuleSettings } from "@cofy/frontend-sdk";

import { CofyModuleEditor } from "../../src/components/cofy-module-editor.js";
import type { YamlEditorChange } from "../../src/components/cofy-yaml-editor.js";

const stored: ModuleSettings = {
  type: "tariff",
  name: "spot",
  display_name: null,
  description: null,
  source: { type: "entsoe_day_ahead", api_key: "**********", country_code: "BE" },
};

const catalog = [{ type: "tariff", description: "Tariff", schema: { type: "object" } }];

function stubApi(): ApiClient {
  const fetchStub = (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const request = input instanceof Request ? input : new Request(input, init);
    const path = new URL(request.url).pathname;
    const body = path.endsWith("/allowed-modules") ? catalog : [stored];
    return Promise.resolve(
      new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } }),
    );
  };
  return new ApiClient({ fetch: fetchStub, baseUrl: "http://localhost" });
}

async function mount(): Promise<CofyModuleEditor> {
  const api = stubApi();
  const element = new CofyModuleEditor();
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

/** What the editor would report after someone typed *text*. */
function type(element: CofyModuleEditor, text: string): void {
  const detail: YamlEditorChange = { text, value: { type: "tariff", name: "spot", edited: true }, syntaxErrors: [] };
  element.shadowRoot!
    .querySelector("cofy-yaml-editor")!
    .dispatchEvent(new CustomEvent<YamlEditorChange>("yaml-change", { detail }));
}

describe("cofy-module-editor", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("shows the stored module, with unset fields left out", async () => {
    const element = await mount();

    const text = element.shadowRoot!.querySelector("cofy-yaml-editor")!.text;

    expect(text).toContain("name: spot");
    expect(text).not.toContain("display_name");
    expect(text).not.toContain("null");
  });

  it("puts the original document back into the editor on discard", async () => {
    // The host has to track what the editor holds; otherwise discarding sets the property to
    // the value it already had, Lit sees no change, and the edits stay on screen.
    const element = await mount();
    const original = element.shadowRoot!.querySelector("cofy-yaml-editor")!.text;

    type(element, "type: tariff\nname: spot\nedited: true\n");
    await element.updateComplete;
    expect(element.shadowRoot!.querySelector("cofy-yaml-editor")!.text).toContain("edited");

    element.shadowRoot!.querySelectorAll("cds-button")[1]!.dispatchEvent(new MouseEvent("click"));
    await element.updateComplete;

    expect(element.shadowRoot!.querySelector("cofy-yaml-editor")!.text).toBe(original);
  });

  it("enables the actions only once there is something to save", async () => {
    const element = await mount();
    const buttons = (): NodeListOf<Element> => element.shadowRoot!.querySelectorAll("cds-button");

    expect(buttons()[0]!.hasAttribute("disabled")).toBe(true);
    expect(buttons()[1]!.hasAttribute("disabled")).toBe(true);

    type(element, "type: tariff\nname: spot\nedited: true\n");
    await element.updateComplete;

    expect(buttons()[0]!.hasAttribute("disabled")).toBe(false);
    expect(buttons()[1]!.hasAttribute("disabled")).toBe(false);
  });
});
