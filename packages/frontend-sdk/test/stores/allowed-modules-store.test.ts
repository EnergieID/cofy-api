import { describe, expect, it } from "vitest";

import { AllowedModulesStore } from "../../src/stores/allowed-modules-store.js";
import { stubbedApi } from "../support/api.js";

const catalog = [
  { type: "billing", description: "Billing", schema: { type: "object" } },
  { type: "tariff", description: "Tariff", schema: { type: "object" } },
];

describe("AllowedModulesStore", () => {
  it("loads a community's catalog", async () => {
    const { api, calls } = stubbedApi(() => ({ body: catalog }));
    const store = new AllowedModulesStore(api);

    await store.load("test");

    expect(store.list("test")).toEqual(catalog);
    expect(calls[0]!.path).toBe("/management/communities/test/allowed-modules");
  });

  it("caches indefinitely, because a schema only changes when the server does", async () => {
    const { api, calls } = stubbedApi(() => ({ body: catalog }));
    const store = new AllowedModulesStore(api);

    await store.ensure("test");
    await store.ensure("test");

    expect(calls).toHaveLength(1);
  });

  it("finds one allowed type, and reports an unknown one as absent", async () => {
    const { api } = stubbedApi(() => ({ body: catalog }));
    const store = new AllowedModulesStore(api);
    await store.ensure("test");

    expect(store.find("test", "billing")?.description).toBe("Billing");
    expect(store.find("test", "nope")).toBeUndefined();
  });

  it("keeps catalogs of different communities apart", async () => {
    const { api } = stubbedApi((call) =>
      call.path.includes("/other/") ? { body: [catalog[0]] } : { body: catalog },
    );
    const store = new AllowedModulesStore(api);

    await store.ensure("test");
    await store.ensure("other");

    expect(store.list("test")).toHaveLength(2);
    expect(store.list("other")).toHaveLength(1);
  });

  it("captures a failure rather than throwing", async () => {
    const { api } = stubbedApi(() => ({ status: 404, body: { status: 404, detail: "no community" } }));
    const store = new AllowedModulesStore(api);

    await store.load("nope");

    expect(store.error?.isNotFound).toBe(true);
  });
});
