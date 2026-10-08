import { describe, expect, it } from "vitest";

import { CofyStore } from "../../src/core/cofy-store.js";
import { stubbedApi } from "../support/api.js";
import type { Call, StubResponse } from "../support/stub-fetch.js";

const billing = { type: "billing", name: "default" };
const live = { state: "live", revision: 1, running_revision: 1 };
const me = { email: "ann@example.com", name: "Ann", system_admin: false, permissions: [] };
const community = { slug: "test", title: "Test", module_count: 0, revision: 1, api_url: "http://localhost/test/" };

/** Answers every request the way the API would, for a community "test". */
function answer(call: Call): StubResponse {
  if (call.method === "DELETE") return { status: 204 };
  if (call.path === "/auth/me") return { body: me };
  if (call.path.endsWith("/status")) return { body: live };
  if (call.path === "/management/communities") return { body: call.method === "GET" ? [community] : community };
  if (call.path.endsWith("/grants")) return { body: { email: "bob@example.com", role: "community_admin", bound: false } };
  if (call.path.includes("/secrets")) return { body: call.method === "GET" ? [] : { name: "key", description: null } };
  if (call.path.includes("/resources")) return { body: call.method === "GET" ? [] : { type: "source", name: "s", value: {} } };
  return { body: call.method === "GET" ? [billing] : billing };
}

function cofy(): { store: CofyStore; calls: Call[] } {
  const { api, calls } = stubbedApi(answer);
  return { store: new CofyStore(api, { pathname: "/", search: "", hash: "" } as Location), calls };
}

/** The requests made since *from*, as `METHOD path`. */
function requestsSince(calls: Call[], from: number): string[] {
  return calls.slice(from).map((call) => `${call.method} ${call.path}`);
}

/** Let background fetches settle. */
async function flush(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
}

describe("CofyStore", () => {
  it.each([
    ["a module", (store: CofyStore): Promise<unknown> => store.modules.replace("test", billing, billing)],
    [
      "a resource",
      (store: CofyStore): Promise<unknown> => store.resources.create("test", { type: "source", name: "s", value: {} }),
    ],
    ["a secret", (store: CofyStore): Promise<unknown> => store.secrets.delete("test", "key")],
  ])("makes a community's status out of date on a write to %s", async (_, write) => {
    const { store, calls } = cofy();
    await store.status.fetch("test");

    await write(store);
    const from = calls.length;
    store.status.get("test");
    await flush();

    expect(requestsSince(calls, from)).toEqual(["GET /management/communities/test/status"]);
  });

  it("recounts the communities' modules when one is created or deleted, not when it is replaced", async () => {
    const { store, calls } = cofy();
    await store.communities.fetch();

    await store.modules.replace("test", billing, billing);
    let from = calls.length;
    store.communities.all();
    await flush();
    expect(requestsSince(calls, from)).toEqual([]);

    await store.modules.delete("test", billing);
    from = calls.length;
    store.communities.all();
    await flush();
    expect(requestsSince(calls, from)).toEqual(["GET /management/communities"]);
  });

  it.each([
    [
      "given",
      (store: CofyStore): Promise<unknown> =>
        store.grants.create("test", { email: "bob@example.com", role: "community_admin" }),
      ["GET /auth/me"],
    ],
    [
      "revoked",
      (store: CofyStore): Promise<unknown> => store.grants.delete("test", "bob@example.com"),
      ["GET /auth/me", "GET /management/communities"],
    ],
  ])("makes who is logged in out of date when a grant is %s, and the communities they see when revoked", async (_, write, expected) => {
    // The grant may be their own.
    const { store, calls } = cofy();
    await Promise.all([store.session.fetch(), store.communities.fetch()]);

    await write(store);
    const from = calls.length;
    store.session.get();
    store.communities.all();
    await flush();

    expect(requestsSince(calls, from)).toEqual(expected);
  });

  it("makes everything about a community out of date when a grant to it is revoked, which may be their own", async () => {
    const { store, calls } = cofy();
    await Promise.all([store.modules.fetch("test"), store.secrets.fetch("test"), store.modules.fetch("other")]);

    await store.grants.delete("test", "bob@example.com");
    const from = calls.length;
    store.modules.all("test");
    store.secrets.all("test");
    store.modules.all("other");
    await flush();

    expect(requestsSince(calls, from)).toEqual([
      "GET /management/communities/test/modules",
      "GET /management/communities/test/secrets",
    ]);
  });

  it("makes who is logged in out of date after creating a community, which gives them a role on it", async () => {
    const { store, calls } = cofy();
    await store.session.fetch();

    await store.communities.create({ slug: "test", title: "Test" });
    const from = calls.length;
    store.session.get();
    await flush();

    expect(requestsSince(calls, from)).toEqual(["GET /auth/me"]);
  });

  it("forgets everything about a deleted community", async () => {
    const { store } = cofy();
    await Promise.all([store.modules.fetch("test"), store.status.fetch("test"), store.modules.fetch("other")]);

    await store.communities.delete("test");

    expect(store.modules.all("test")).toBeUndefined();
    expect(store.status.get("test")).toBeUndefined();
    expect(store.modules.all("other")).toEqual([billing]);
  });
});
