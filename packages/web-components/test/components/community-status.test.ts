import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiClient, CofyStore, type CommunityStatus } from "@cofy/frontend-sdk";

import { CofyCommunityStatus } from "../../src/components/community/cofy-community-status.js";
import type { CofyI18n } from "../../src/i18n/cofy-i18n.js";
import { testI18n } from "../support/i18n.js";

let i18n: CofyI18n;

function status(state: CommunityStatus["state"]): CommunityStatus {
  return { state, revision: 2, running_revision: state === "live" ? 2 : 1 };
}

/** A store whose API answers each status request with the next of *answers*, repeating the last. */
function storeAnswering(...answers: CommunityStatus[]): { store: CofyStore; requests: string[] } {
  const requests: string[] = [];
  const fetchStub = (input: RequestInfo | URL): Promise<Response> => {
    requests.push(new URL(input instanceof Request ? input.url : input.toString()).pathname);
    const answer = answers[Math.min(requests.length, answers.length) - 1];
    return Promise.resolve(
      new Response(JSON.stringify(answer), { status: 200, headers: { "content-type": "application/json" } }),
    );
  };
  return { store: new CofyStore(new ApiClient({ fetch: fetchStub, baseUrl: "http://localhost" })), requests };
}

async function settle(element: CofyCommunityStatus): Promise<void> {
  await element.updateComplete;
  await vi.advanceTimersByTimeAsync(0);
  await element.updateComplete;
}

async function mount(store?: CofyStore): Promise<CofyCommunityStatus> {
  const element = new CofyCommunityStatus();
  element.i18n = i18n;
  if (store !== undefined) element.cofy = store;
  element.slug = "demo";
  document.body.append(element);
  await settle(element);
  return element;
}

function badge(element: CofyCommunityStatus): HTMLElement | null {
  return element.shadowRoot!.querySelector("wa-badge");
}

describe("cofy-community-status", () => {
  beforeEach(async () => {
    // Loaded first, as loading the translations needs time to pass.
    i18n = await testI18n();
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    document.body.replaceChildren();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it.each([
    ["live", "Live", "success"],
    ["pending", "Changes pending", "warning"],
    ["unavailable", "Unavailable", "danger"],
  ] as const)("shows %s as a badge", async (state, label, variant) => {
    const element = await mount(storeAnswering(status(state)).store);

    expect(badge(element)?.textContent?.trim()).toBe(label);
    expect(badge(element)?.getAttribute("variant")).toBe(variant);
    expect(element.shadowRoot!.querySelector("wa-tooltip")?.textContent?.trim()).not.toBe("");
  });

  it("asks for its own community", async () => {
    const { store, requests } = storeAnswering(status("live"));

    await mount(store);

    expect(requests).toEqual(["/management/communities/demo/status"]);
  });

  it("shows nothing without an answer", async () => {
    expect(badge(await mount())).toBeNull();
  });

  it("asks again soon while changes are pending, until they are not", async () => {
    const { store, requests } = storeAnswering(status("pending"), status("live"));
    const element = await mount(store);

    await vi.advanceTimersByTimeAsync(CofyCommunityStatus.PENDING_INTERVAL);
    await element.updateComplete;

    expect(requests).toHaveLength(2);
    expect(badge(element)?.textContent?.trim()).toBe("Live");

    await vi.advanceTimersByTimeAsync(CofyCommunityStatus.PENDING_INTERVAL);
    expect(requests).toHaveLength(2);

    await vi.advanceTimersByTimeAsync(CofyCommunityStatus.SETTLED_INTERVAL);
    expect(requests).toHaveLength(3);
  });

  it("asks again right away when a write makes it out of date", async () => {
    const { store, requests } = storeAnswering(status("live"), status("pending"));
    const element = await mount(store);

    await store.secrets.delete("demo", "acc");
    await settle(element);

    expect(requests.filter((path) => path.endsWith("/status"))).toHaveLength(2);
    expect(badge(element)?.textContent?.trim()).toBe("Changes pending");
  });

  it("stops asking once it is taken out", async () => {
    const { store, requests } = storeAnswering(status("pending"));
    const element = await mount(store);

    element.remove();
    await vi.advanceTimersByTimeAsync(CofyCommunityStatus.SETTLED_INTERVAL * 2);

    expect(requests).toHaveLength(1);
  });
});
