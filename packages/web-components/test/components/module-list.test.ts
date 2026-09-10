import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiClient, ModuleStore, type ModuleSettings } from "@cofy/frontend-sdk";

import { CofyModuleList } from "../../src/components/cofy-module-list.js";

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
  element.store = new ModuleStore(stubApi(state));
  element.slug = "test";
  document.body.append(element);
  await element.updateComplete;
  await new Promise((resolve) => setTimeout(resolve, 10));
  await element.updateComplete;
  return element;
}

function rowNames(element: CofyModuleList): string[] {
  return Array.from(element.shadowRoot!.querySelectorAll("cds-table-row")).map(
    (row) => row.getAttribute("selection-name") ?? "",
  );
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

  it("carries its own title and toolbar, so a page adds no chrome", async () => {
    const element = await mount({ modules: [...modules] });
    const root = element.shadowRoot!;

    expect(root.querySelector("cds-table-header-title")?.textContent?.trim()).toBe("Modules");
    expect(root.querySelector("cds-table-toolbar-search")).not.toBeNull();
    expect(root.querySelector("cds-table-batch-actions")).not.toBeNull();
  });

  it("still shows the remaining rows after a delete", async () => {
    // Carbon's `is-sortable` reorders row elements behind Lit's back, which left the table
    // empty after any list change - the store had rows and the DOM had none.
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

    element.shadowRoot!.querySelectorAll("cds-table-row")[1]!.dispatchEvent(new MouseEvent("click"));

    expect(events).toEqual([{ slug: "test", id: { type: "tariff", name: "kiwatt" } }]);
  });

  it("does not open a module when the click was on its checkbox", async () => {
    const element = await mount({ modules: [...modules] });
    const events: unknown[] = [];
    element.addEventListener("module-edit", () => events.push("opened"));

    const row = element.shadowRoot!.querySelectorAll("cds-table-row")[0]!;
    const checkbox = row.shadowRoot!.querySelector("cds-checkbox")!;
    checkbox.dispatchEvent(new MouseEvent("click", { bubbles: true, composed: true }));

    expect(events).toEqual([]);
  });

  it("asks for the toolbar's create action rather than routing itself", async () => {
    const element = await mount({ modules: [...modules] });
    const events: unknown[] = [];
    element.addEventListener("module-create", (event) => events.push((event as CustomEvent).detail));

    element.shadowRoot!.querySelector("cds-table-toolbar-content cds-button")!.dispatchEvent(new MouseEvent("click"));

    expect(events).toEqual([{ slug: "test" }]);
  });

  it("deletes every selected module after one confirmation", async () => {
    const state = { modules: [...modules] };
    const element = await mount(state);
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);

    for (const name of ["tariff:entsoe", "billing:default"]) {
      element.shadowRoot!.querySelector(`cds-table-row[selection-name="${name}"]`)!.setAttribute("selected", "");
    }
    element.shadowRoot!.querySelector("cds-table-batch-actions cds-button")!.dispatchEvent(new MouseEvent("click"));
    await new Promise((resolve) => setTimeout(resolve, 20));
    await element.updateComplete;

    expect(confirm).toHaveBeenCalledTimes(1);
    expect(state.modules.map((module) => module.name)).toEqual(["kiwatt"]);
    expect(rowNames(element)).toEqual(["tariff:kiwatt"]);
  });

  it("deletes nothing when the confirmation is dismissed", async () => {
    const state = { modules: [...modules] };
    const element = await mount(state);
    vi.spyOn(window, "confirm").mockReturnValue(false);

    element.shadowRoot!.querySelector('cds-table-row[selection-name="tariff:entsoe"]')!.setAttribute("selected", "");
    element.shadowRoot!.querySelector("cds-table-batch-actions cds-button")!.dispatchEvent(new MouseEvent("click"));
    await new Promise((resolve) => setTimeout(resolve, 20));

    expect(state.modules).toHaveLength(3);
  });

  it("names the single module in the confirmation, and counts several", async () => {
    const element = await mount({ modules: [...modules] });
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);

    element.shadowRoot!.querySelector('cds-table-row[selection-name="tariff:entsoe"]')!.setAttribute("selected", "");
    element.shadowRoot!.querySelector("cds-table-batch-actions cds-button")!.dispatchEvent(new MouseEvent("click"));
    await new Promise((resolve) => setTimeout(resolve, 10));
    expect(confirm.mock.calls[0]![0]).toContain("Delete entsoe? Its configuration");

    element.shadowRoot!.querySelector('cds-table-row[selection-name="tariff:kiwatt"]')!.setAttribute("selected", "");
    element.shadowRoot!.querySelector("cds-table-batch-actions cds-button")!.dispatchEvent(new MouseEvent("click"));
    await new Promise((resolve) => setTimeout(resolve, 10));
    expect(confirm.mock.calls[1]![0]).toContain("Delete 2 modules? Their configuration");
  });
});
