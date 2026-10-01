import { beforeEach, describe, expect, it, vi } from "vitest";
import { ContextProvider } from "@lit/context";
import { ApiClient, ResourceStore, type ResourceSettings } from "@cofy/frontend-sdk";

import { CofyResourceList } from "../../src/components/resource/cofy-resource-list.js";
import { i18nContext } from "../../src/context.js";
import { testI18n } from "../support/i18n.js";

interface Community {
  resources: ResourceSettings[];
  /** Resources the server refuses to delete, as still referenced. */
  inUse: string[];
}

const resources: ResourceSettings[] = [
  { type: "tariff", name: "dynamic", description: "Dynamic tariff" },
  { type: "source", name: "day_ahead" },
];

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

function stubApi(state: Community): ApiClient {
  const fetchStub = (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const request = input instanceof Request ? input : new Request(input, init);
    const name = new URL(request.url).pathname.split("/").at(-1)!;
    if (request.method === "DELETE") {
      if (state.inUse.includes(name)) {
        const detail = `Resource '${name}' is still referenced by module tariff:spot`;
        return Promise.resolve(json({ status: 409, title: "Conflict", detail, code: "resource-in-use" }, 409));
      }
      state.resources = state.resources.filter((resource) => resource.name !== name);
      return Promise.resolve(new Response(null, { status: 204 }));
    }
    return Promise.resolve(json(state.resources));
  };
  return new ApiClient({ fetch: fetchStub, baseUrl: "http://localhost" });
}

async function mount(state: Community): Promise<CofyResourceList> {
  // Provided rather than set, so the elements the list renders read the same translations.
  const host = document.createElement("div");
  new ContextProvider(host, { context: i18nContext, initialValue: await testI18n() });
  document.body.append(host);
  const element = new CofyResourceList();
  element.store = new ResourceStore(stubApi(state));
  element.slug = "test";
  host.append(element);
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
    const element = await mount({ resources: [...resources], inUse: [] });

    expect(rowNames(element)).toEqual(["dynamic", "day_ahead"]);
    expect(element.shadowRoot!.querySelector('tr[data-key="dynamic"]')!.textContent).toContain("Dynamic tariff");
  });

  it("opens a resource when its row is clicked", async () => {
    const element = await mount({ resources: [...resources], inUse: [] });
    const events: unknown[] = [];
    element.addEventListener("resource-edit", (event) => events.push((event as CustomEvent).detail));

    element.shadowRoot!.querySelectorAll("tr[data-key]")[1]!.dispatchEvent(new MouseEvent("click"));

    expect(events).toEqual([{ slug: "test", name: "day_ahead" }]);
  });

  it("deletes a resource after asking", async () => {
    const state = { resources: [...resources], inUse: [] };
    const element = await mount(state);
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);

    await pressDelete(element, "dynamic");

    expect(confirm).toHaveBeenCalledTimes(1);
    expect(state.resources.map((resource) => resource.name)).toEqual(["day_ahead"]);
    expect(rowNames(element)).toEqual(["day_ahead"]);
  });

  it("shows why the server refused to delete a resource still in use, keeping the list", async () => {
    const state = { resources: [...resources], inUse: ["day_ahead"] };
    const element = await mount(state);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    await pressDelete(element, "day_ahead");

    expect(element.shadowRoot!.querySelector("cofy-problem-details")!.problem!.message).toContain("tariff:spot");
    expect(rowNames(element)).toEqual(["dynamic", "day_ahead"]);
  });
});
