import { describe, expect, it } from "vitest";

import { TokenStore } from "../../src/stores/token-store.js";
import { failingApi, stubbedApi } from "../support/api.js";

const app = { name: "app", description: "Our app", expires: null };
const meter = { name: "meter", description: null, expires: "2030-01-01T00:00:00Z" };

describe("TokenStore", () => {
  it("loads a community's tokens", async () => {
    const { api, calls } = stubbedApi(() => ({ body: [app, meter] }));
    const store = new TokenStore(api);

    await store.fetch("test");

    expect(store.all("test")).toEqual([app, meter]);
    expect(store.get("test", "meter")).toEqual(meter);
    expect(calls[0]!.path).toBe("/management/communities/test/tokens");
  });

  it("creates a token, handing its key to the caller but not to the cache", async () => {
    const created = { ...meter, key: "cofy_secret" };
    const { api, calls } = stubbedApi((call) => (call.method === "GET" ? { body: [app] } : { body: created }));
    const store = new TokenStore(api);
    await store.fetch("test");

    const result = await store.create("test", { name: "meter", expires: "2030-01-01T00:00:00Z" });

    expect(calls[1]).toMatchObject({ method: "POST", body: { name: "meter", expires: "2030-01-01T00:00:00Z" } });
    expect(result.key).toBe("cofy_secret");
    expect(store.all("test")).toEqual([app, meter]);
  });

  it("updates a token", async () => {
    const updated = { ...app, description: "Renamed" };
    const { api, calls } = stubbedApi((call) => (call.method === "GET" ? { body: [app] } : { body: updated }));
    const store = new TokenStore(api);
    await store.fetch("test");

    await store.replace("test", "app", { name: "app", description: "Renamed" });

    expect(calls[1]).toMatchObject({ method: "PUT", path: "/management/communities/test/tokens/app" });
    expect(store.get("test", "app")).toEqual(updated);
  });

  it("drops a removed token from a loaded cache", async () => {
    const { api } = stubbedApi((call) => (call.method === "GET" ? { body: [app] } : { status: 204 }));
    const store = new TokenStore(api);
    await store.fetch("test");

    await store.delete("test", "app");

    expect(store.all("test")).toEqual([]);
  });

  it("converts a raw fetch failure into a ProblemError on create", async () => {
    await expect(new TokenStore(failingApi()).create("test", { name: "a" })).rejects.toMatchObject({
      name: "ProblemError",
    });
  });
});
