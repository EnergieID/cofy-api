import { beforeEach, describe, expect, it } from "vitest";
import { AllowedModulesStore, ApiClient, ModuleStore } from "@cofy/frontend-sdk";

import { CofyModuleCreate } from "../../src/components/cofy-module-create.js";

const catalog = [
  {
    type: "billing",
    description: "Billing module",
    schema: {
      type: "object",
      properties: { type: { const: "billing" }, name: { type: "string", default: "default" } },
      required: ["name"],
    },
  },
  {
    type: "tariff",
    description: "Tariff module",
    schema: {
      type: "object",
      properties: {
        type: { const: "tariff", default: "tariff" },
        name: { type: "string" },
        // recursive: a formula may contain further formulas
        formula: { $ref: "#/$defs/Formula" },
      },
      required: ["name", "formula"],
      $defs: {
        Formula: {
          type: "object",
          properties: { kind: { const: "index", default: "index" }, inner: { $ref: "#/$defs/Formula" } },
          required: ["kind", "inner"],
        },
      },
    },
  },
];

function stubApi(): ApiClient {
  const fetchStub = (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const request = input instanceof Request ? input : new Request(input, init);
    const path = new URL(request.url).pathname;
    const body = path.endsWith("/allowed-modules") ? catalog : [];
    return Promise.resolve(
      new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } }),
    );
  };
  return new ApiClient({ fetch: fetchStub, baseUrl: "http://localhost" });
}

async function mount(preload = true): Promise<CofyModuleCreate> {
  const api = stubApi();
  const allowedModules = new AllowedModulesStore(api);
  if (preload) await allowedModules.ensure("test");

  const element = new CofyModuleCreate();
  element.allowedModules = allowedModules;
  element.moduleStore = new ModuleStore(api);
  element.slug = "test";
  document.body.append(element);
  await element.updateComplete;
  return element;
}

/** What the editor currently holds; the component's own copy is private. */
function document_(element: CofyModuleCreate): string {
  return element.shadowRoot!.querySelector("cofy-yaml-editor")?.text ?? "";
}

function selectType(element: CofyModuleCreate, type: string): void {
  element.shadowRoot!
    .querySelector("cds-select")!
    .dispatchEvent(new CustomEvent("cds-select-selected", { detail: { value: type } }));
}

describe("cofy-module-create", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("offers every allowed module type", async () => {
    const element = await mount();

    const items = element.shadowRoot!.querySelectorAll("cds-select-item");

    expect(Array.from(items).map((item) => item.getAttribute("value"))).toEqual(["", "billing", "tariff"]);
  });

  it("renders the catalog that arrives after the first render", async () => {
    const element = await mount(false);

    // the component starts with nothing loaded and must react to the store filling in
    await new Promise((resolve) => setTimeout(resolve, 10));
    await element.updateComplete;

    const items = element.shadowRoot!.querySelectorAll("cds-select-item");
    expect(Array.from(items).map((item) => item.getAttribute("value"))).toEqual(["", "billing", "tariff"]);
  });

  it("seeds a document for every allowed type, including the recursive ones", async () => {
    // These schemas are recursive; seeding used to overflow the stack for four of the six,
    // which left the previous type's document in place with no visible error.
    const element = await mount();

    for (const type of ["billing", "tariff"]) {
      selectType(element, type);
      await element.updateComplete;
      expect(document_(element)).toContain(`type: ${type}`);
    }
  });

  it("replaces the document when the type is changed again", async () => {
    const element = await mount();

    selectType(element, "billing");
    await element.updateComplete;
    const billing = document_(element);

    selectType(element, "tariff");
    await element.updateComplete;

    expect(document_(element)).not.toBe(billing);
    expect(document_(element)).toContain("type: tariff");
  });

  it("leaves unset fields out of the seeded document", async () => {
    const element = await mount();

    selectType(element, "billing");
    await element.updateComplete;

    expect(document_(element)).not.toContain("null");
  });

  it("shows no editor until a type is chosen", async () => {
    const element = await mount();

    expect(element.shadowRoot!.querySelector("cofy-yaml-editor")).toBeNull();
  });
});
