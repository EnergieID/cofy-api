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

    await store.ensure("test");
    await store.ensure("test");

    expect(store.list("test")).toEqual(catalog);
    expect(calls).toHaveLength(1);
    expect(calls[0]!.path).toBe("/management/communities/test/allowed-resources");
  });

  it("finds one allowed kind, and reports an unknown one as absent", async () => {
    const { api } = stubbedApi(() => ({ body: catalog }));
    const store = new AllowedResourcesStore(api);
    await store.ensure("test");

    expect(store.find("test", "tariff")?.description).toBe("An energy cost tariff.");
    expect(store.find("test", "nope")).toBeUndefined();
  });
});
