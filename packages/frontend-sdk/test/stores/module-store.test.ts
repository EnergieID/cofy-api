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
      expect(store.list("test")).toBeUndefined();
    });

    it("appends to an already-loaded cache", async () => {
      const { api } = stubbedApi((call) =>
        call.method === "GET" ? { body: [billing] } : { body: { type: "billing", name: "second" } },
      );
      const store = new ModuleStore(api);
      await store.load("test");

      await store.create("test", { type: "billing", name: "second" });

      expect(store.list("test")?.map((m) => m.name)).toEqual(["default", "second"]);
    });
  });

  describe("remove", () => {
    it("drops the module from an already-loaded cache", async () => {
      const { api } = stubbedApi((call) => (call.method === "GET" ? { body: [billing] } : { status: 204 }));
      const store = new ModuleStore(api);
      await store.load("test");

      await store.remove("test", billing);

      expect(store.list("test")).toEqual([]);
    });
  });

  describe("ensure/invalidate", () => {
    it("loads once, and reloads after invalidate", async () => {
      const { api, calls } = stubbedApi(() => ({ body: [billing] }));
      const store = new ModuleStore(api);

      await store.ensure("test");
      await store.ensure("test");
      expect(calls).toHaveLength(1);

      store.invalidate("test");
      await store.ensure("test");

      expect(calls).toHaveLength(2);
    });
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

      await expect(store.remove("test", billing)).rejects.toMatchObject({ name: "ProblemError" });
    });
  });
});
