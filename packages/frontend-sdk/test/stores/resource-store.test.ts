import { describe, expect, it } from "vitest";

import { ResourceStore } from "../../src/stores/resource-store.js";
import { failingApi, stubbedApi } from "../support/api.js";

const key = { type: "secret", name: "entsoe_key", value: "**********" };
const prices = { type: "source", name: "day_ahead", value: { type: "entsoe_day_ahead" } };
const wind = { type: "source", name: "wind", value: { type: "energyid_production" } };
const alias = { type: "source", name: "alias", value: { type: "ref", name: "day_ahead" } };

describe("ResourceStore", () => {
  it("loads a community's resources", async () => {
    const { api, calls } = stubbedApi(() => ({ body: [key, prices] }));
    const store = new ResourceStore(api);

    await store.load("test");

    expect(store.list("test")).toEqual([key, prices]);
    expect(store.find("test", "day_ahead")).toEqual(prices);
    expect(calls[0]!.path).toBe("/management/communities/test/resources");
  });

  it("picks the resources a field can reference, by kind and by what they hold", async () => {
    const { api } = stubbedApi(() => ({ body: [key, prices, wind, alias] }));
    const store = new ResourceStore(api);
    await store.load("test");

    expect(store.fitting("test", { kind: "source", types: ["entsoe_day_ahead"] })).toEqual([prices, alias]);
    expect(store.fitting("test", { kind: "source" })).toEqual([prices, wind, alias]);
    expect(store.fitting("test", { kind: "secret" })).toEqual([key]);
    expect(store.fitting("other", { kind: "secret" })).toEqual([]);
  });

  describe("create", () => {
    it("does not cache a partial list when the community was never loaded", async () => {
      const { api } = stubbedApi(() => ({ body: key }));
      const store = new ResourceStore(api);

      await store.create("test", key);

      expect(store.list("test")).toBeUndefined();
    });

    it("appends to an already-loaded cache", async () => {
      const { api } = stubbedApi((call) => (call.method === "GET" ? { body: [key] } : { body: prices }));
      const store = new ResourceStore(api);
      await store.load("test");

      await store.create("test", prices);

      expect(store.list("test")?.map((resource) => resource.name)).toEqual(["entsoe_key", "day_ahead"]);
    });
  });

  it("replaces a cached resource with what the server stored", async () => {
    const stored = { ...key, description: "ENTSO-E" };
    const { api, calls } = stubbedApi((call) => (call.method === "GET" ? { body: [key] } : { body: stored }));
    const store = new ResourceStore(api);
    await store.load("test");

    await store.replace("test", "entsoe_key", { ...key, description: "ENTSO-E" });

    expect(calls[1]).toMatchObject({ method: "PUT", path: "/management/communities/test/resources/entsoe_key" });
    expect(store.find("test", "entsoe_key")).toEqual(stored);
  });

  it("drops a removed resource from an already-loaded cache", async () => {
    const { api } = stubbedApi((call) => (call.method === "GET" ? { body: [key] } : { status: 204 }));
    const store = new ResourceStore(api);
    await store.load("test");

    await store.remove("test", "entsoe_key");

    expect(store.list("test")).toEqual([]);
  });

  it("fetches what references a resource", async () => {
    const usages = { modules: [{ type: "tariff", name: "spot" }], resources: [] };
    const { api, calls } = stubbedApi(() => ({ body: usages }));
    const store = new ResourceStore(api);

    expect(await store.usages("test", "day_ahead")).toEqual(usages);
    expect(calls[0]!.path).toBe("/management/communities/test/resources/day_ahead/usages");
  });

  it("surfaces a conflicting delete as a ProblemError", async () => {
    const { api } = stubbedApi(() => ({ status: 409, body: { status: 409, detail: "still referenced" } }));
    const store = new ResourceStore(api);

    await expect(store.remove("test", "day_ahead")).rejects.toMatchObject({ isConflict: true });
  });

  it("converts a raw fetch failure into a ProblemError on create", async () => {
    const store = new ResourceStore(failingApi());

    await expect(store.create("test", key)).rejects.toMatchObject({ name: "ProblemError" });
  });
});
