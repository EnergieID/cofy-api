import { beforeEach, describe, expect, it } from "vitest";
import { AllowedResourcesStore, ApiClient, ResourceStore, type ResourceSettings } from "@cofy/frontend-sdk";

import { CofyResourceEditor } from "../../src/components/resource/cofy-resource-editor.js";
import { testI18n } from "../support/i18n.js";

const stored: ResourceSettings = { type: "source", name: "day_ahead", description: null, value: { type: "entsoe_day_ahead" } };

const catalog = [{ type: "source", description: "A timeseries source.", schema: { type: "object" } }];

function stubApi(puts: unknown[]): ApiClient {
  const fetchStub = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const request = input instanceof Request ? input : new Request(input, init);
    const path = new URL(request.url).pathname;
    let body: unknown = path.endsWith("/allowed-resources") ? catalog : [stored];
    if (request.method === "PUT") {
      body = await request.json();
      puts.push({ path, body });
    }
    return new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });
  };
  return new ApiClient({ fetch: fetchStub, baseUrl: "http://localhost" });
}

async function mount(puts: unknown[] = []): Promise<CofyResourceEditor> {
  const api = stubApi(puts);
  const element = new CofyResourceEditor();
  element.i18n = await testI18n();
  element.resourceStore = new ResourceStore(api);
  element.allowedResources = new AllowedResourcesStore(api);
  element.slug = "test";
  element.name = "day_ahead";
  document.body.append(element);
  await element.updateComplete;
  await new Promise((resolve) => setTimeout(resolve, 20));
  await element.updateComplete;
  return element;
}

function edit(element: CofyResourceEditor, value: ResourceSettings): void {
  element.shadowRoot!
    .querySelector("cofy-module-form")!
    .dispatchEvent(new CustomEvent("module-form-change", { detail: { value }, bubbles: true, composed: true }));
}

function saveButton(element: CofyResourceEditor): Element {
  return element.shadowRoot!.querySelectorAll("footer wa-button")[0]!;
}

describe("cofy-resource-editor", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("opens the stored resource in the form, labelled as a resource kind", async () => {
    const element = await mount();
    const form = element.shadowRoot!.querySelector("cofy-module-form")!;

    expect(form.value).toEqual(stored);
    expect(form.typeLabel).toBe("Resource kind");
    expect(element.shadowRoot!.querySelector('cofy-heading [slot="title"]')?.textContent?.trim()).toBe(
      "Edit resource",
    );
  });

  it("saves an edit against the resource's name", async () => {
    const puts: unknown[] = [];
    const element = await mount(puts);

    edit(element, { ...stored, description: "ENTSO-E" });
    await element.updateComplete;
    saveButton(element).dispatchEvent(new MouseEvent("click"));
    await new Promise((resolve) => setTimeout(resolve, 20));

    expect(puts).toEqual([
      { path: "/management/communities/test/resources/day_ahead", body: { ...stored, description: "ENTSO-E" } },
    ]);
  });

  it("blocks save when the edit renames the resource", async () => {
    const element = await mount();

    edit(element, { ...stored, name: "renamed" });
    await element.updateComplete;

    expect(saveButton(element).hasAttribute("disabled")).toBe(true);
    expect(element.shadowRoot!.textContent).toContain("A resource's name is its identity");
  });
});
