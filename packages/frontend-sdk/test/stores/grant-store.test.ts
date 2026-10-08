import { describe, expect, it } from "vitest";

import { GrantStore } from "../../src/stores/grant-store.js";
import { failingApi, stubbedApi } from "../support/api.js";

const ann = { email: "ann@example.com", role: "community_admin" as const, bound: true };
const bob = { email: "bob@example.com", role: "community_admin" as const, bound: false };

describe("GrantStore", () => {
  it("loads a community's grants", async () => {
    const { api, calls } = stubbedApi(() => ({ body: [ann, bob] }));
    const store = new GrantStore(api);

    await store.fetch("test");

    expect(store.all("test")).toEqual([ann, bob]);
    expect(store.get("test", "bob@example.com")).toEqual(bob);
    expect(calls[0]!.path).toBe("/management/communities/test/grants");
  });

  it("grants a role, appending what the server reported to a loaded cache", async () => {
    const { api, calls } = stubbedApi((call) => (call.method === "GET" ? { body: [ann] } : { body: bob }));
    const store = new GrantStore(api);
    await store.fetch("test");

    await store.create("test", { email: "bob@example.com", role: "community_admin" });

    expect(calls[1]).toMatchObject({ method: "POST", body: { email: "bob@example.com", role: "community_admin" } });
    expect(store.all("test")).toEqual([ann, bob]);
  });

  it("changes a role", async () => {
    const { api, calls } = stubbedApi((call) => (call.method === "GET" ? { body: [ann] } : { body: ann }));
    const store = new GrantStore(api);
    await store.fetch("test");

    await store.replace("test", "ann@example.com", { email: "ann@example.com", role: "community_admin" });

    expect(calls[1]).toMatchObject({ method: "PUT", path: "/management/communities/test/grants/ann%40example.com" });
  });

  it("drops a revoked grant from a loaded cache", async () => {
    const { api } = stubbedApi((call) => (call.method === "GET" ? { body: [ann] } : { status: 204 }));
    const store = new GrantStore(api);
    await store.fetch("test");

    await store.delete("test", "ann@example.com");

    expect(store.all("test")).toEqual([]);
  });

  it("converts a raw fetch failure into a ProblemError on create", async () => {
    await expect(
      new GrantStore(failingApi()).create("test", { email: "a@example.com", role: "community_admin" }),
    ).rejects.toMatchObject({ name: "ProblemError" });
  });
});
