import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiClient, ModuleStore, type ModuleSettings } from "@cofy/frontend-sdk";

import { CofyModuleList } from "../../src/components/module/cofy-module-list.js";
import { testI18n } from "../support/i18n.js";

const modules: ModuleSettings[] = [
  { type: "tariff", name: "entsoe" },
  { type: "tariff", name: "kiwatt" },
  { type: "billing", name: "default" },
];

function stubApi(state: { modules: ModuleSettings[] }): ApiClient {
  const fetchStub = (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const request = input instanceof Request ? input : new Request(input, init);
    if (request.method === "DELETE") {
      const name = new URL(request.url).pathname.split("/").pop()!;
      state.modules = state.modules.filter((module) => module.name !== name);
      return Promise.resolve(new Response(null, { status: 204 }));
    }
    return Promise.resolve(
      new Response(JSON.stringify(state.modules), { status: 200, headers: { "content-type": "application/json" } }),
    );
  };
  return new ApiClient({ fetch: fetchStub, baseUrl: "http://localhost" });
}

async function mount(state: { modules: ModuleSettings[] }): Promise<CofyModuleList> {
  const element = new CofyModuleList();
  element.i18n = await testI18n();
  element.store = new ModuleStore(stubApi(state));
  element.slug = "test";
  document.body.append(element);
  await element.updateComplete;
  await new Promise((resolve) => setTimeout(resolve, 10));
  await element.updateComplete;
  return element;
}

function rowNames(element: CofyModuleList): string[] {
  return Array.from(element.shadowRoot!.querySelectorAll("tr[data-key]")).map(
    (row) => row.getAttribute("data-key") ?? "",
  );
}

/** The delete button in the row for *key*. */
function deleteButton(element: CofyModuleList, key: string): HTMLElement {
  return element.shadowRoot!.querySelector<HTMLElement>(`tr[data-key="${key}"] .actions wa-button`)!;
}

describe("cofy-module-list", () => {
  beforeEach(() => {
    document.body.replaceChildren();
    vi.restoreAllMocks();
  });

  it("renders a row per module, keyed by its identity", async () => {
    const element = await mount({ modules: [...modules] });

    expect(rowNames(element)).toEqual(["tariff:entsoe", "tariff:kiwatt", "billing:default"]);
  });

  it("carries its own heading and create action, so a page adds no chrome", async () => {
    const element = await mount({ modules: [...modules] });
    const root = element.shadowRoot!;

    expect(root.querySelector('cofy-heading [slot="title"]')?.textContent?.trim()).toBe("Modules");
    expect(root.querySelector('cofy-heading [slot="actions"]')?.textContent?.trim()).toBe("Add module");
  });

  it("still shows the remaining rows after a delete", async () => {
    // Carbon's `is-sortable` reordered row elements behind Lit's back, which left the table
    // empty after any list change - the store had rows and the DOM had none. A plain table has
    // nothing doing that, but the guarantee is worth keeping under test.
    const state = { modules: [...modules] };
    const element = await mount(state);

    await element.store.remove("test", { type: "tariff", name: "entsoe" });
    await element.updateComplete;

    expect(rowNames(element)).toEqual(["tariff:kiwatt", "billing:default"]);
  });

  it("opens a module when its row is clicked", async () => {
    const element = await mount({ modules: [...modules] });
    const events: unknown[] = [];
    element.addEventListener("module-edit", (event) => events.push((event as CustomEvent).detail));

    element.shadowRoot!.querySelectorAll("tr[data-key]")[1]!.dispatchEvent(new MouseEvent("click"));

    expect(events).toEqual([{ slug: "test", id: { type: "tariff", name: "kiwatt" } }]);
  });

  it("opens a module from the keyboard, which a plain row does not do by itself", async () => {
    const element = await mount({ modules: [...modules] });
    const events: unknown[] = [];
    element.addEventListener("module-edit", (event) => events.push((event as CustomEvent).detail));

    const row = element.shadowRoot!.querySelectorAll("tr[data-key]")[0]!;
    expect(row.getAttribute("tabindex")).toBe("0");
    row.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));

    expect(events).toEqual([{ slug: "test", id: { type: "tariff", name: "entsoe" } }]);
  });

  it("does not open a module when the click was on its delete button", async () => {
    const element = await mount({ modules: [...modules] });
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const events: unknown[] = [];
    element.addEventListener("module-edit", () => events.push("opened"));

    deleteButton(element, "tariff:entsoe").dispatchEvent(new MouseEvent("click", { bubbles: true, composed: true }));

    expect(events).toEqual([]);
  });

  it("asks for the create action rather than routing itself", async () => {
    const element = await mount({ modules: [...modules] });
    const events: unknown[] = [];
    element.addEventListener("module-create", (event) => events.push((event as CustomEvent).detail));

    element.shadowRoot!.querySelector('[slot="actions"]')!.dispatchEvent(new MouseEvent("click"));

    expect(events).toEqual([{ slug: "test" }]);
  });

  it("deletes exactly the module whose button was pressed", async () => {
    const state = { modules: [...modules] };
    const element = await mount(state);
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);

    deleteButton(element, "tariff:entsoe").dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 20));
    await element.updateComplete;

    expect(confirm).toHaveBeenCalledTimes(1);
    expect(state.modules.map((module) => module.name)).toEqual(["kiwatt", "default"]);
    expect(rowNames(element)).toEqual(["tariff:kiwatt", "billing:default"]);
  });

  it("deletes nothing when the confirmation is dismissed", async () => {
    const state = { modules: [...modules] };
    const element = await mount(state);
    vi.spyOn(window, "confirm").mockReturnValue(false);

    deleteButton(element, "tariff:entsoe").dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 20));

    expect(state.modules).toHaveLength(3);
  });

  it("names the module in the confirmation", async () => {
    const element = await mount({ modules: [...modules] });
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);

    deleteButton(element, "tariff:entsoe").dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 10));

    expect(confirm.mock.calls[0]![0]).toContain("Delete entsoe? Its configuration");
  });
});
