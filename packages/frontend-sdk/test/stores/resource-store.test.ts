import { describe, expect, it } from "vitest";

import { ResourceStore } from "../../src/stores/resource-store.js";
import { failingApi, stubbedApi } from "../support/api.js";

const tariff = { type: "tariff", name: "dynamic", value: [] };
const prices = { type: "source", name: "day_ahead", value: { type: "entsoe_day_ahead" } };
const wind = { type: "source", name: "wind", value: { type: "energyid_production" } };
const alias = { type: "source", name: "alias", value: { type: "resource", name: "day_ahead" } };

describe("ResourceStore", () => {
  it("loads a community's resources", async () => {
    const { api, calls } = stubbedApi(() => ({ body: [tariff, prices] }));
    const store = new ResourceStore(api);

    await store.fetch("test");

    expect(store.all("test")).toEqual([tariff, prices]);
    expect(store.get("test", "day_ahead")).toEqual(prices);
    expect(calls[0]!.path).toBe("/management/communities/test/resources");
  });

  it("picks the resources a field can reference, by kind and by what they hold", async () => {
    const { api } = stubbedApi(() => ({ body: [tariff, prices, wind, alias] }));
    const store = new ResourceStore(api);
    await store.fetch("test");

    expect(store.fitting("test", { kind: "source", types: ["entsoe_day_ahead"] })).toEqual([prices, alias]);
    expect(store.fitting("test", { kind: "source" })).toEqual([prices, wind, alias]);
    expect(store.fitting("test", { kind: "tariff" })).toEqual([tariff]);
    expect(store.fitting("other", { kind: "tariff" })).toEqual([]);
  });

  describe("create", () => {
    it("does not cache a partial list when the community was never loaded", async () => {
      const { api } = stubbedApi(() => ({ body: tariff }));
      const store = new ResourceStore(api);

      await store.create("test", tariff);

      expect(store.all("test")).toBeUndefined();
    });

    it("appends to an already-loaded cache", async () => {
      const { api } = stubbedApi((call) => (call.method === "GET" ? { body: [tariff] } : { body: prices }));
      const store = new ResourceStore(api);
      await store.fetch("test");

      await store.create("test", prices);

      expect(store.all("test")?.map((resource) => resource.name)).toEqual(["dynamic", "day_ahead"]);
    });
  });

  it("replaces a cached resource with what the server stored", async () => {
    const stored = { ...tariff, description: "ENTSO-E" };
    const { api, calls } = stubbedApi((call) => (call.method === "GET" ? { body: [tariff] } : { body: stored }));
    const store = new ResourceStore(api);
    await store.fetch("test");

    await store.replace("test", "dynamic", { ...tariff, description: "ENTSO-E" });

    expect(calls[1]).toMatchObject({ method: "PUT", path: "/management/communities/test/resources/dynamic" });
    expect(store.get("test", "dynamic")).toEqual(stored);
  });

  it("drops a removed resource from an already-loaded cache", async () => {
    const { api } = stubbedApi((call) => (call.method === "GET" ? { body: [tariff] } : { status: 204 }));
    const store = new ResourceStore(api);
    await store.fetch("test");

    await store.delete("test", "dynamic");

    expect(store.all("test")).toEqual([]);
  });

  it("surfaces a conflicting delete as a ProblemError", async () => {
    const { api } = stubbedApi(() => ({ status: 409, body: { status: 409, detail: "still referenced" } }));
    const store = new ResourceStore(api);

    await expect(store.delete("test", "day_ahead")).rejects.toMatchObject({ isConflict: true });
  });

  it("converts a raw fetch failure into a ProblemError on create", async () => {
    const store = new ResourceStore(failingApi());

    await expect(store.create("test", tariff)).rejects.toMatchObject({ name: "ProblemError" });
  });
});
