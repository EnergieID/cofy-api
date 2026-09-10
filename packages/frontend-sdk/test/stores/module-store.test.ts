import { beforeEach, describe, expect, it } from "vitest";

import { ModuleStore } from "../../src/stores/module-store.js";
import { stubbedApi } from "../support/api.js";
import type { Call } from "../support/stub-fetch.js";

const billing = { type: "billing", name: "default" };
const tariff = { type: "tariff", name: "spot", source: { type: "entsoe_day_ahead", api_key: "**********" } };

describe("ModuleStore", () => {
  let calls: Call[];
  let store: ModuleStore;

  beforeEach(() => {
    const stub = stubbedApi((call) => {
      if (call.method === "DELETE") return { status: 204 };
      if (call.method === "POST") return { status: 201, body: call.body };
      if (call.method === "PUT") return { body: call.body };
      return { body: [billing, tariff] };
    });
    calls = stub.calls;
    store = new ModuleStore(stub.api);
  });

  it("reports nothing cached before a load", () => {
    expect(store.list("test")).toBeUndefined();
  });

  it("caches per community", async () => {
    await store.load("test");

    expect(store.list("test")).toEqual([billing, tariff]);
    expect(store.list("other")).toBeUndefined();
  });

  it("ensure fetches once and then serves the cache", async () => {
    await store.ensure("test");
    await store.ensure("test");

    expect(calls.filter((c) => c.method === "GET")).toHaveLength(1);
  });

  it("finds a module by its type and name", async () => {
    await store.load("test");

    expect(store.find("test", { type: "tariff", name: "spot" })).toEqual(tariff);
    expect(store.find("test", { type: "tariff", name: "missing" })).toBeUndefined();
  });

  it("appends a created module to the cached list without refetching", async () => {
    await store.load("test");

    await store.create("test", { type: "billing", name: "extra" });

    expect(store.list("test")).toHaveLength(3);
    expect(calls.filter((c) => c.method === "GET")).toHaveLength(1);
  });

  it("swaps a replaced module in place, leaving the rest of the list alone", async () => {
    await store.load("test");
    const withDisplayName = { ...tariff, display_name: "Spot prices" };

    await store.replace("test", { type: "tariff", name: "spot" }, withDisplayName);

    expect(store.list("test")).toEqual([billing, withDisplayName]);
  });

  it("addresses a module by type and name in the path", async () => {
    await store.load("test");

    await store.replace("test", { type: "tariff", name: "spot" }, tariff);

    expect(calls.at(-1)!.path).toBe("/management/communities/test/modules/tariff/spot");
  });

  it("drops a removed module from the cached list", async () => {
    await store.load("test");

    await store.remove("test", { type: "billing", name: "default" });

    expect(store.list("test")).toEqual([tariff]);
  });

  it("invalidate makes the next ensure refetch", async () => {
    await store.ensure("test");

    store.invalidate("test");
    await store.ensure("test");

    expect(calls.filter((c) => c.method === "GET")).toHaveLength(2);
  });

  it("notifies subscribers for the community that changed", async () => {
    const seen: (string | undefined)[] = [];
    store.modules.subscribe((_s, key) => seen.push(key), "test");

    await store.load("test");

    expect(seen).toEqual(["test"]);
  });

  it("does not notify subscribers of another community", async () => {
    const seen: (string | undefined)[] = [];
    store.modules.subscribe((_s, key) => seen.push(key), "other");

    await store.load("test");

    expect(seen).toEqual([]);
  });

  it("lets a write error reach the caller rather than swallowing it", async () => {
    const stub = stubbedApi((call) =>
      call.method === "POST" ? { status: 409, body: { status: 409, detail: "exists" } } : { body: [] },
    );
    const failing = new ModuleStore(stub.api);

    await expect(failing.create("test", billing)).rejects.toThrow("exists");
  });

  it("captures a read failure on the store rather than throwing", async () => {
    const stub = stubbedApi(() => ({ status: 422, body: { status: 422, detail: "bad config" } }));
    const failing = new ModuleStore(stub.api);

    await failing.load("test");

    expect(failing.error?.status).toBe(422);
    expect(failing.list("test")).toBeUndefined();
  });
});
