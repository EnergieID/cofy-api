import { beforeEach, describe, expect, it } from "vitest";
import { ApiClient, CommunityStore, type CommunityInfo } from "@cofy/frontend-sdk";

import { CofyCommunityList } from "../../src/components/community/cofy-community-list.js";
import { testI18n } from "../support/i18n.js";

const communities: CommunityInfo[] = [
  { slug: "demo", title: "Demo Energy Community", description: "", debug_mode: false, module_count: 2 },
  { slug: "riverside", title: "", description: "", debug_mode: false, module_count: 0 },
];

function stubApi(rows: CommunityInfo[]): ApiClient {
  const fetchStub = (): Promise<Response> =>
    Promise.resolve(
      new Response(JSON.stringify(rows), { status: 200, headers: { "content-type": "application/json" } }),
    );
  return new ApiClient({ fetch: fetchStub, baseUrl: "http://localhost" });
}

async function mount(rows: CommunityInfo[] = communities): Promise<CofyCommunityList> {
  const element = new CofyCommunityList();
  element.i18n = await testI18n();
  element.store = new CommunityStore(stubApi(rows));
  document.body.append(element);
  await element.updateComplete;
  await new Promise((resolve) => setTimeout(resolve, 10));
  await element.updateComplete;
  return element;
}

function rows(element: CofyCommunityList): string[] {
  return Array.from(element.shadowRoot!.querySelectorAll("tr[data-slug]")).map(
    (row) => row.getAttribute("data-slug") ?? "",
  );
}

describe("cofy-community-list", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("renders a row per community", async () => {
    expect(rows(await mount())).toEqual(["demo", "riverside"]);
  });

  it("falls back to the slug when a community has no title", async () => {
    const element = await mount();

    const cells = Array.from(element.shadowRoot!.querySelectorAll("tr[data-slug] td:first-child"));

    expect(cells.map((cell) => cell.textContent.trim())).toEqual(["Demo Energy Community", "riverside"]);
  });

  it("carries its own heading, so a page adds no chrome", async () => {
    const element = await mount();

    expect(element.shadowRoot!.querySelector('cofy-heading [slot="title"]')?.textContent?.trim()).toBe(
      "Communities",
    );
  });

  it("says so when there are no communities", async () => {
    const element = await mount([]);

    expect(rows(element)).toEqual([]);
    expect(element.shadowRoot!.querySelector("tr.empty")?.textContent?.trim()).toBe(
      "No communities are configured.",
    );
  });

  it("asks to be taken to a community rather than routing itself", async () => {
    const element = await mount();
    const events: unknown[] = [];
    element.addEventListener("community-selected", (event) => events.push((event as CustomEvent).detail));

    element.shadowRoot!.querySelector('tr[data-slug="riverside"]')!.dispatchEvent(new MouseEvent("click"));

    expect(events).toEqual([{ slug: "riverside" }]);
  });

  it("opens a community from the keyboard, which a plain row does not do by itself", async () => {
    const element = await mount();
    const events: unknown[] = [];
    element.addEventListener("community-selected", (event) => events.push((event as CustomEvent).detail));

    const row = element.shadowRoot!.querySelector('tr[data-slug="demo"]')!;
    expect(row.getAttribute("tabindex")).toBe("0");
    row.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));

    expect(events).toEqual([{ slug: "demo" }]);
  });
});
