import { describe, expect, it } from "vitest";

import { AllowedResourcesStore } from "../../src/stores/allowed-resources-store.js";
import { stubbedApi } from "../support/api.js";

const catalog = [
  { type: "source", description: "A timeseries source.", schema: { type: "object" } },
  { type: "tariff", description: "An energy cost tariff.", schema: { type: "object" } },
];

describe("AllowedResourcesStore", () => {
  it("loads a community's catalog once", async () => {
    const { api, calls } = stubbedApi(() => ({ body: catalog }));
    const store = new AllowedResourcesStore(api);

    store.all("test");
    await store.fetch("test");

    expect(store.all("test")).toEqual(catalog);
    expect(calls).toHaveLength(1);
    expect(calls[0]!.path).toBe("/management/communities/test/allowed-resources");
  });

  it("finds one allowed kind, and reports an unknown one as absent", async () => {
    const { api } = stubbedApi(() => ({ body: catalog }));
    const store = new AllowedResourcesStore(api);
    await store.fetch("test");

    expect(store.get("test", "tariff")?.description).toBe("An energy cost tariff.");
    expect(store.get("test", "nope")).toBeUndefined();
  });
});
