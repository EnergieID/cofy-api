import { beforeEach, describe, expect, it } from "vitest";
import { ContextProvider } from "@lit/context";
import { ApiClient, CofyStore, type JsonSchema, type ResourceSettings } from "@cofy/frontend-sdk";

import type { MenuAction } from "../../../src/components/form/cofy-action-menu.js";
import type { CofyAnyForm } from "../../../src/components/form/cofy-any-form.js";
import { CofyReferableForm } from "../../../src/components/form/cofy-referable-form.js";
import { defaultFieldRegistry } from "../../../src/components/form/field-registry.js";
import { cofyStoreContext, communitySlugContext, i18nContext } from "../../../src/context.js";
import type { CofySaveResourceDialog } from "../../../src/components/resource/cofy-save-resource-dialog.js";
import { testI18n } from "../../support/i18n.js";

const refSettings: JsonSchema = {
  type: "object",
  properties: { type: { const: "resource" }, name: { type: "string" } },
  required: ["name"],
};

/** A single input, which can also be a reference to a resource holding a note. */
const note: JsonSchema = {
  oneOf: [{ type: "string", format: "password", writeOnly: true }, { $ref: "#/$defs/RefSettings" }],
  "x-referable": { kind: "note" },
  $defs: { RefSettings: refSettings },
};

/** A source field: one of the tariff sources, or a reference to a source resource holding one. */
const source: JsonSchema = {
  oneOf: [
    { type: "object", properties: { type: { const: "entsoe_day_ahead" } } },
    { $ref: "#/$defs/RefSettings" },
  ],
  "x-referable": { kind: "source", types: ["entsoe_day_ahead"] },
  $defs: { RefSettings: refSettings },
};

const resources: ResourceSettings[] = [
  { type: "note", name: "greeting", value: "hello" },
  { type: "source", name: "day_ahead", description: "Belgian prices", value: { type: "entsoe_day_ahead" } },
  { type: "source", name: "wind", value: { type: "energyid_production" } },
];

interface Posted {
  path: string;
  body: unknown;
}

function stubApi(posted: Posted[]): ApiClient {
  const fetchStub = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const request = input instanceof Request ? input : new Request(input, init);
    const path = new URL(request.url).pathname;
    let body: unknown = resources;
    if (request.method === "POST") {
      body = await request.json();
      posted.push({ path, body });
    }
    return new Response(JSON.stringify(body), {
      status: request.method === "POST" ? 201 : 200,
      headers: { "content-type": "application/json" },
    });
  };
  return new ApiClient({ fetch: fetchStub, baseUrl: "http://localhost" });
}

async function settle(element: HTMLElement & { updateComplete: Promise<unknown> }): Promise<void> {
  await element.updateComplete;
  await new Promise((resolve) => setTimeout(resolve, 10));
  await element.updateComplete;
}

/** Mounted inside providers of the store and community, as an editor provides them - the dialog it opens reads them too. */
async function mount(schema: JsonSchema, value: unknown, posted: Posted[] = []): Promise<CofyReferableForm> {
  const host = document.createElement("div");
  new ContextProvider(host, { context: cofyStoreContext, initialValue: new CofyStore(stubApi(posted)) });
  new ContextProvider(host, { context: communitySlugContext, initialValue: "test" });
  new ContextProvider(host, { context: i18nContext, initialValue: await testI18n() });
  document.body.append(host);

  const element = new CofyReferableForm();
  element.schema = schema;
  element.root = schema;
  element.pointer = "/api_key";
  element.label = "Api Key";
  element.value = value;
  host.append(element);
  await settle(element);
  return element;
}

/** Every value this field reported, as the form around it would apply them. */
function changes(element: CofyReferableForm): unknown[] {
  const values: unknown[] = [];
  element.addEventListener("field-change", (event) => {
    const value = (event as CustomEvent<{ value: unknown }>).detail.value;
    values.push(value);
    element.value = value;
  });
  return values;
}

function valueForm(element: CofyReferableForm): CofyAnyForm {
  return element.shadowRoot!.querySelector("cofy-any-form")!;
}

/** The actions on the value: in the field's own menu for a single input, or handed to a container's form. */
function valueActions(element: CofyReferableForm): readonly MenuAction[] {
  return element.shadowRoot!.querySelector("cofy-action-menu")?.actions ?? valueForm(element).menuActions;
}

function run(actions: readonly MenuAction[], id: string): void {
  actions.find((action) => action.id === id)!.run();
}

function refMenu(element: CofyReferableForm): readonly MenuAction[] {
  return element.shadowRoot!.querySelector("cofy-action-menu")!.actions;
}

describe("cofy-referable-form", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("is what a referable field dispatches to, ahead of the union form", () => {
    expect(defaultFieldRegistry.getFirstMatch(note, note)?.tag).toBe("cofy-referable-form");
  });

  it("edits a single input as itself, under its label with the actions beside it", async () => {
    const element = await mount(note, "real");
    const form = valueForm(element);

    expect(form.schema).toEqual((note["oneOf"] as JsonSchema[])[0]);
    expect(form.bare).toBe(true);
    expect(element.shadowRoot!.querySelector("cofy-field-shell")!.label).toBe("Api Key");
    expect(valueActions(element).map((action) => action.id)).toEqual(["use-resource", "save-as-resource"]);
  });

  it("hands the actions to a container, which shows them beside its own label", async () => {
    const element = await mount(source, { type: "entsoe_day_ahead" });
    const form = valueForm(element);

    expect(form.bare).toBe(false);
    expect(form.label).toBe("Api Key");
    expect(form.menuActions.map((action) => action.id)).toEqual(["use-resource", "save-as-resource"]);
  });

  it("only offers a resource once one fits", async () => {
    const tariff: JsonSchema = { ...note, "x-referable": { kind: "tariff" } };
    const element = await mount(tariff, "real");

    expect(valueActions(element).map((action) => action.id)).toEqual(["save-as-resource"]);
  });

  it("leaves a field that can neither use nor save a resource as it is", async () => {
    const tariff: JsonSchema = { ...note, "x-referable": { kind: "tariff" } };
    // no fitting resource to use, and nothing entered yet to save as one
    const element = await mount(tariff, undefined);

    expect(element.shadowRoot!.querySelector("cofy-action-menu")).toBeNull();
    expect(valueForm(element).bare).toBe(false);
  });

  it("picks the resource under the field's own label, not one of its own", async () => {
    const element = await mount(source, { type: "resource", name: "day_ahead" });

    expect(element.shadowRoot!.querySelector("cofy-field-shell")!.label).toBe("Api Key");
    expect(element.shadowRoot!.querySelector("wa-select")!.hasAttribute("label")).toBe(false);
  });

  it("switches to a reference, and back to the value it replaced", async () => {
    const element = await mount(note, "real");
    const values = changes(element);

    run(valueActions(element), "use-resource");
    await settle(element);
    expect(element.shadowRoot!.querySelector("cofy-any-form")).toBeNull();
    expect(element.shadowRoot!.querySelector("wa-select")).not.toBeNull();

    run(refMenu(element), "specify-value");
    await settle(element);

    expect(values).toEqual([{ type: "resource", name: "" }, "real"]);
    expect(valueForm(element)).not.toBeNull();
  });

  it("offers only the resources of its kind that hold what the field accepts", async () => {
    const element = await mount(source, { type: "resource", name: "day_ahead" });

    const options = Array.from(element.shadowRoot!.querySelectorAll("wa-option"));
    expect(options.map((option) => option.getAttribute("value"))).toEqual(["day_ahead"]);
    expect(options[0]!.textContent).toContain("Belgian prices");
  });

  it("references the resource picked", async () => {
    const element = await mount(source, { type: "resource", name: "" });
    const values = changes(element);

    const picker = element.shadowRoot!.querySelector<HTMLElement & { value: string }>("wa-select")!;
    picker.value = "day_ahead";
    picker.dispatchEvent(new Event("change", { bubbles: true }));

    expect(values).toEqual([{ type: "resource", name: "day_ahead" }]);
  });

  it("saves the value as a resource, and references it once saved", async () => {
    const posted: Posted[] = [];
    const value = { type: "entsoe_day_ahead", country_code: "BE" };
    const element = await mount(source, value, posted);
    const values = changes(element);

    run(valueActions(element), "save-as-resource");
    await settle(element);
    const dialog = element.shadowRoot!.querySelector<CofySaveResourceDialog>("cofy-save-resource-dialog")!;
    expect(dialog.open).toBe(true);

    const [name, description] = Array.from(dialog.shadowRoot!.querySelectorAll<HTMLElement & { value: string }>("wa-input"));
    name!.value = "be_prices";
    name!.dispatchEvent(new Event("input"));
    description!.value = "Belgian prices";
    description!.dispatchEvent(new Event("input"));
    await dialog.updateComplete;
    dialog.shadowRoot!.querySelector<HTMLElement>('wa-button[variant="brand"]')!.click();
    await settle(element);

    expect(posted).toEqual([
      {
        path: "/management/communities/test/resources",
        body: { type: "source", name: "be_prices", description: "Belgian prices", value },
      },
    ]);
    expect(values).toEqual([{ type: "resource", name: "be_prices" }]);
    // now referencing the resource, so showing the picker - and no dialog - instead
    expect(element.shadowRoot!.querySelector("cofy-save-resource-dialog")).toBeNull();
    expect(element.shadowRoot!.querySelector<HTMLElement & { value: string }>("wa-select")!.value).toBe("be_prices");
  });
});
