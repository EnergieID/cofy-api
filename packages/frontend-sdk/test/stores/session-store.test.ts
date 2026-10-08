import { describe, expect, it } from "vitest";

import { SessionStore } from "../../src/stores/session-store.js";
import { stubbedApi } from "../support/api.js";

const me = {
  email: "ann@example.com",
  name: "Ann",
  system_admin: false,
  permissions: [
    { slug: null, permissions: [{ action: "read" as const, subject: "community" as const }] },
    {
      slug: "demo",
      permissions: [
        { action: "read" as const, subject: "community" as const },
        { action: "read" as const, subject: "grants" as const },
      ],
    },
  ],
};

/** A page at *hash*, recording where it was sent. */
function page(hash: string): Location & { assigned: string[] } {
  const assigned: string[] = [];
  const location = { pathname: "/", search: "", hash, assign: (url: string): number => assigned.push(url), assigned };
  return location as unknown as Location & { assigned: string[] };
}

describe("SessionStore", () => {
  it("loads who is logged in", async () => {
    const { api, calls } = stubbedApi(() => ({ body: me }));
    const store = new SessionStore(api, page(""));

    await store.fetch();

    expect(store.get()).toEqual(me);
    expect(calls[0]!.path).toBe("/auth/me");
  });

  it("keeps the failure when nobody is logged in", async () => {
    const { api } = stubbedApi(() => ({ status: 401, body: { status: 401, code: "not-authenticated" } }));
    const store = new SessionStore(api, page(""));

    await store.fetch().catch(() => {});

    expect(store.get()).toBeUndefined();
    expect(store.error()?.status).toBe(401);
  });

  it("asks again who is logged in once invalidated", async () => {
    const { api, calls } = stubbedApi(() => ({ body: me }));
    const store = new SessionStore(api, page(""));
    await store.fetch();

    store.invalidate();
    store.get();
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(calls).toHaveLength(2);
  });

  it("logs in by sending the browser to the API, to come back to the page shown", () => {
    const location = page("#/communities/test");
    const { api } = stubbedApi(() => undefined);

    new SessionStore(api, location).login();

    expect(location.assigned).toEqual(["/auth/login?return_to=%2F%23%2Fcommunities%2Ftest"]);
  });

  it("answers whether an action on a subject is allowed in a community", async () => {
    const { api } = stubbedApi(() => ({ body: me }));
    const store = new SessionStore(api, page(""));
    await store.fetch();

    expect(store.can("read", "grants", "demo")).toBe(true);
    expect(store.can("write", "grants", "demo")).toBe(false);
    expect(store.can("read", "grants", "elsewhere")).toBe(false);
  });

  it("answers for outside any one community under a null slug", async () => {
    const { api } = stubbedApi(() => ({ body: me }));
    const store = new SessionStore(api, page(""));
    await store.fetch();

    expect(store.can("read", "community", null)).toBe(true);
    expect(store.can("write", "community", null)).toBe(false);
  });

  it("allows nothing before anyone is known to be logged in", () => {
    const { api } = stubbedApi(() => ({ body: me }));

    expect(new SessionStore(api, page("")).can("read", "community", null)).toBe(false);
  });
});
