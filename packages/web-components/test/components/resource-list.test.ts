import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiClient, ResourceStore, type ResourceSettings } from "@cofy/frontend-sdk";

import { CofyResourceList } from "../../src/components/resource/cofy-resource-list.js";
import { testI18n } from "../support/i18n.js";

interface Community {
  resources: ResourceSettings[];
  /** Resource name -> the module ids referencing it. */
  usedBy: Record<string, string[]>;
}

const resources: ResourceSettings[] = [
  { type: "secret", name: "entsoe_key", description: "ENTSO-E" },
  { type: "source", name: "day_ahead" },
];

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });
}

function stubApi(state: Community): ApiClient {
  const fetchStub = (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const request = input instanceof Request ? input : new Request(input, init);
    const segments = new URL(request.url).pathname.split("/");
    if (segments.at(-1) === "usages") {
      const modules = (state.usedBy[segments.at(-2)!] ?? []).map((id) => {
        const [type, name] = id.split(":");
        return { type, name };
      });
      return Promise.resolve(json({ modules, resources: [] }));
    }
    if (request.method === "DELETE") {
      state.resources = state.resources.filter((resource) => resource.name !== segments.at(-1));
      return Promise.resolve(new Response(null, { status: 204 }));
    }
    return Promise.resolve(json(state.resources));
  };
  return new ApiClient({ fetch: fetchStub, baseUrl: "http://localhost" });
}

async function mount(state: Community): Promise<CofyResourceList> {
  const element = new CofyResourceList();
  element.i18n = await testI18n();
  element.store = new ResourceStore(stubApi(state));
  element.slug = "test";
  document.body.append(element);
  await element.updateComplete;
  await new Promise((resolve) => setTimeout(resolve, 10));
  await element.updateComplete;
  return element;
}

function rowNames(element: CofyResourceList): string[] {
  return Array.from(element.shadowRoot!.querySelectorAll("tr[data-key]")).map((row) => row.getAttribute("data-key") ?? "");
}

async function pressDelete(element: CofyResourceList, name: string): Promise<void> {
  element.shadowRoot!
    .querySelector<HTMLElement>(`tr[data-key="${name}"] .actions wa-button`)!
    .dispatchEvent(new MouseEvent("click", { bubbles: true }));
  await new Promise((resolve) => setTimeout(resolve, 20));
  await element.updateComplete;
}

describe("cofy-resource-list", () => {
  beforeEach(() => {
    document.body.replaceChildren();
    vi.restoreAllMocks();
  });

  it("renders a row per resource with its kind and description", async () => {
    const element = await mount({ resources: [...resources], usedBy: {} });

    expect(rowNames(element)).toEqual(["entsoe_key", "day_ahead"]);
    expect(element.shadowRoot!.querySelector('tr[data-key="entsoe_key"]')!.textContent).toContain("ENTSO-E");
  });

  it("opens a resource when its row is clicked", async () => {
    const element = await mount({ resources: [...resources], usedBy: {} });
    const events: unknown[] = [];
    element.addEventListener("resource-edit", (event) => events.push((event as CustomEvent).detail));

    element.shadowRoot!.querySelectorAll("tr[data-key]")[1]!.dispatchEvent(new MouseEvent("click"));

    expect(events).toEqual([{ slug: "test", name: "day_ahead" }]);
  });

  it("tells what still references a resource instead of deleting it", async () => {
    const state = { resources: [...resources], usedBy: { day_ahead: ["tariff:spot"] } };
    const element = await mount(state);
    const alert = vi.spyOn(window, "alert").mockImplementation(() => undefined);
    const confirm = vi.spyOn(window, "confirm");

    await pressDelete(element, "day_ahead");

    expect(alert.mock.calls[0]![0]).toContain("tariff:spot");
    expect(confirm).not.toHaveBeenCalled();
    expect(state.resources.map((resource) => resource.name)).toEqual(["entsoe_key", "day_ahead"]);
  });

  it("deletes an unreferenced resource after asking", async () => {
    const state = { resources: [...resources], usedBy: {} };
    const element = await mount(state);
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);

    await pressDelete(element, "entsoe_key");

    expect(confirm).toHaveBeenCalledTimes(1);
    expect(state.resources.map((resource) => resource.name)).toEqual(["day_ahead"]);
    expect(rowNames(element)).toEqual(["day_ahead"]);
  });
});
