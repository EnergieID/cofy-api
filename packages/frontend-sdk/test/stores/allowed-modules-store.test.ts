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

    await store.fetch("test");

    expect(store.all("test")).toEqual(catalog);
    expect(calls[0]!.path).toBe("/management/communities/test/allowed-modules");
  });

  it("fetches once however often it is read, because a schema only changes when the server does", async () => {
    const { api, calls } = stubbedApi(() => ({ body: catalog }));
    const store = new AllowedModulesStore(api);

    store.all("test");
    await store.fetch("test");
    store.all("test");

    expect(calls).toHaveLength(1);
  });

  it("finds one allowed type, and reports an unknown one as absent", async () => {
    const { api } = stubbedApi(() => ({ body: catalog }));
    const store = new AllowedModulesStore(api);
    await store.fetch("test");

    expect(store.get("test", "billing")?.description).toBe("Billing");
    expect(store.get("test", "nope")).toBeUndefined();
  });

  it("keeps catalogs of different communities apart", async () => {
    const { api } = stubbedApi((call) =>
      call.path.includes("/other/") ? { body: [catalog[0]] } : { body: catalog },
    );
    const store = new AllowedModulesStore(api);

    await store.fetch("test");
    await store.fetch("other");

    expect(store.all("test")).toHaveLength(2);
    expect(store.all("other")).toHaveLength(1);
  });

  it("keeps a failure to show", async () => {
    const { api } = stubbedApi(() => ({ status: 404, body: { status: 404, detail: "no community" } }));
    const store = new AllowedModulesStore(api);

    await store.fetch("nope").catch(() => {});

    expect(store.error("nope")?.isNotFound).toBe(true);
    expect(store.error("test")).toBeNull();
  });
});
