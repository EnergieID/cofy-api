import { beforeEach, describe, expect, it } from "vitest";
import { AllowedModulesStore, ApiClient, ModuleStore } from "@cofy/frontend-sdk";

import { CofyModuleCreate } from "../../src/components/module/cofy-module-create.js";
import { testI18n } from "../support/i18n.js";

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
  element.i18n = await testI18n();
  element.allowedModules = allowedModules;
  element.moduleStore = new ModuleStore(api);
  element.slug = "test";
  document.body.append(element);
  await element.updateComplete;
  // `cofy-module-form` (and its own type wa-select) mounts recursively and needs its own tick
  // to finish its first render before its options are ready to interact with.
  await new Promise((resolve) => setTimeout(resolve, 0));
  return element;
}

/** The type picker now lives inside `cofy-module-form`, itself part of the create component's own form. */
function moduleForm(element: CofyModuleCreate): HTMLElement & { value: unknown; shadowRoot: ShadowRoot } {
  return element.shadowRoot!.querySelector("cofy-module-form") as HTMLElement & { value: unknown; shadowRoot: ShadowRoot };
}

/** What the form currently holds; the component's own copy is private. */
function seeded(element: CofyModuleCreate): Record<string, unknown> | undefined {
  return moduleForm(element).value as Record<string, unknown> | undefined;
}

async function selectType(element: CofyModuleCreate, type: string): Promise<void> {
  // Set the value and fire a plain `change`, the way the real control does - rather than
  // fabricating a detail payload the component would never otherwise see.
  const select = moduleForm(element).shadowRoot.querySelector<HTMLElement & { value: string }>("wa-select")!;
  select.value = type;
  select.dispatchEvent(new Event("change", { bubbles: true }));
  await element.updateComplete;
  // `cofy-module-form` re-renders one tick after cofy-module-create's own update settles.
  await new Promise((resolve) => setTimeout(resolve, 0));
}

describe("cofy-module-create", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("offers every allowed module type", async () => {
    const element = await mount();

    const items = moduleForm(element).shadowRoot.querySelectorAll("wa-option");

    expect(Array.from(items).map((item) => item.getAttribute("value"))).toEqual(["billing", "tariff"]);
  });

  it("renders the catalog that arrives after the first render", async () => {
    const element = await mount(false);

    // the component starts with nothing loaded and must react to the store filling in
    await new Promise((resolve) => setTimeout(resolve, 10));
    await element.updateComplete;

    const items = moduleForm(element).shadowRoot.querySelectorAll("wa-option");
    expect(Array.from(items).map((item) => item.getAttribute("value"))).toEqual(["billing", "tariff"]);
  });

  it("seeds a document for every allowed type, including the recursive ones", async () => {
    // These schemas are recursive; seeding used to overflow the stack for four of the six,
    // which left the previous type's document in place with no visible error.
    const element = await mount();

    for (const type of ["billing", "tariff"]) {
      await selectType(element, type);
      expect(seeded(element)?.["type"]).toBe(type);
    }
  });

  it("replaces the document when the type is changed again", async () => {
    const element = await mount();

    await selectType(element, "billing");
    const billing = seeded(element);

    await selectType(element, "tariff");

    expect(seeded(element)).not.toEqual(billing);
    expect(seeded(element)?.["type"]).toBe("tariff");
  });

  it("leaves unset, undefaulted fields out of the seeded document", async () => {
    const element = await mount();

    await selectType(element, "billing");

    expect(Object.values(seeded(element)!)).not.toContain(null);
    expect(Object.values(seeded(element)!)).not.toContain(undefined);
  });

  it("shows no fields below the picker until a type is chosen", async () => {
    const element = await mount();

    expect(moduleForm(element).shadowRoot.querySelector("cofy-object-form")).toBeNull();
    expect(moduleForm(element).shadowRoot.querySelector("cofy-yaml-editor")).toBeNull();
  });

  it("shows no footer until a type is chosen", async () => {
    const element = await mount();

    expect(element.shadowRoot!.querySelector("footer")).toBeNull();
  });

  it("shows a fixed title in its heading, and no view toggle until a type is chosen", async () => {
    const element = await mount();

    expect(element.shadowRoot!.querySelector('cofy-heading [slot="title"]')?.textContent?.trim()).toBe(
      "Add module",
    );
    expect(element.shadowRoot!.querySelector('cofy-heading wa-button[slot="actions"]')).toBeNull();
  });

  it("shows the view toggle once a type is chosen, and hides the picker once YAML is selected", async () => {
    const element = await mount();
    await selectType(element, "billing");

    const toggle = element.shadowRoot!.querySelector<HTMLElement>('cofy-heading wa-button[slot="actions"]');
    expect(toggle).not.toBeNull();
    expect(moduleForm(element).shadowRoot.querySelector("wa-select")).not.toBeNull();

    toggle!.dispatchEvent(new MouseEvent("click"));
    await element.updateComplete;

    expect(moduleForm(element).shadowRoot.querySelector("wa-select")).toBeNull();
    expect(moduleForm(element).shadowRoot.querySelector("cofy-yaml-editor")).not.toBeNull();
  });

  it("shows validation issues as a plain badge, not a clickable list", async () => {
    const element = await mount();
    // the recursive Formula bottoms out its own required `inner` as null - a real issue.
    await selectType(element, "tariff");

    const badge = element.shadowRoot!.querySelector("wa-badge");
    expect(badge).not.toBeNull();
    expect(badge!.getAttribute("variant")).toBe("danger");
    expect(badge!.textContent).toMatch(/blocks? saving/);
    expect(element.shadowRoot!.querySelector("ul.issues")).toBeNull();
  });
});
