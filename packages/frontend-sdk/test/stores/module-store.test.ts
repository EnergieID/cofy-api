import { describe, expect, it } from "vitest";

import { ModuleStore } from "../../src/stores/module-store.js";
import { failingApi, stubbedApi } from "../support/api.js";

const billing = { type: "billing", name: "default" };

describe("ModuleStore", () => {
  describe("create", () => {
    it("does not cache a partial list when the community was never loaded", async () => {
      const { api } = stubbedApi(() => ({ body: billing }));
      const store = new ModuleStore(api);

      await store.create("test", billing);

      // A cache write here would mark "test" as loaded with only the module just created,
      // so a later `ensure` would never fetch the real list and hide every other module.
      expect(store.all("test")).toBeUndefined();
    });

    it("appends to an already-loaded cache", async () => {
      const { api } = stubbedApi((call) =>
        call.method === "GET" ? { body: [billing] } : { body: { type: "billing", name: "second" } },
      );
      const store = new ModuleStore(api);
      await store.fetch("test");

      await store.create("test", { type: "billing", name: "second" });

      expect(store.all("test")?.map((m) => m.name)).toEqual(["default", "second"]);
    });
  });

  describe("remove", () => {
    it("drops the module from an already-loaded cache", async () => {
      const { api } = stubbedApi((call) => (call.method === "GET" ? { body: [billing] } : { status: 204 }));
      const store = new ModuleStore(api);
      await store.fetch("test");

      await store.delete("test", billing);

      expect(store.all("test")).toEqual([]);
    });
  });

  it("asks for a community's modules, and the module by its type and name", async () => {
    const { api, calls } = stubbedApi((call) => (call.method === "GET" ? { body: [billing] } : { body: billing }));
    const store = new ModuleStore(api);
    await store.fetch("test");

    await store.replace("test", billing, billing);

    expect(calls.map((call) => `${call.method} ${call.path}`)).toEqual([
      "GET /management/communities/test/modules",
      "PUT /management/communities/test/modules/billing/default",
    ]);
    expect(store.get("test", { type: "billing", name: "default" })).toEqual(billing);
  });

  it("reports a write with the identity of the module it touched", async () => {
    const changes: unknown[] = [];
    const { api } = stubbedApi(() => ({ body: billing }));
    const store = new ModuleStore(api, (change) => changes.push(change));

    await store.create("test", billing);

    expect(changes).toEqual([{ action: "create", scope: ["test"], id: { type: "billing", name: "default" } }]);
  });

  describe("error wrapping", () => {
    it("converts a raw fetch failure into a ProblemError on create", async () => {
      const store = new ModuleStore(failingApi());

      await expect(store.create("test", billing)).rejects.toMatchObject({ name: "ProblemError" });
    });

    it("converts a raw fetch failure into a ProblemError on replace", async () => {
      const store = new ModuleStore(failingApi());

      await expect(store.replace("test", billing, billing)).rejects.toMatchObject({ name: "ProblemError" });
    });

    it("converts a raw fetch failure into a ProblemError on remove", async () => {
      const store = new ModuleStore(failingApi());

      await expect(store.delete("test", billing)).rejects.toMatchObject({ name: "ProblemError" });
    });
  });
});
