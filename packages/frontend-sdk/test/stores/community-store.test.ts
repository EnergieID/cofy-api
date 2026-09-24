import { describe, expect, it } from "vitest";

import { CommunityStore } from "../../src/stores/community-store.js";
import { failingApi, stubbedApi } from "../support/api.js";

describe("CommunityStore mutations", () => {
  it("updates the cached listing in place", async () => {
    const { api } = stubbedApi(() => ({ body: { slug: "test", title: "Renamed", module_count: 0 } }));
    const store = new CommunityStore(api);
    store.communities = [{ slug: "test", title: "Test", module_count: 0 }];

    const updated = await store.update("test", { title: "Renamed" });

    expect(updated.title).toBe("Renamed");
    expect(store.communities).toEqual([{ slug: "test", title: "Renamed", module_count: 0 }]);
  });

  it("removes a community from the cached listing, clearing the selection if it was current", async () => {
    const { api } = stubbedApi(() => ({ status: 204 }));
    const store = new CommunityStore(api);
    store.communities = [{ slug: "test", title: "Test", module_count: 0 }];
    store.select("test");

    await store.remove("test");

    expect(store.communities).toEqual([]);
    expect(store.currentSlug).toBeNull();
  });
});

describe("CommunityStore error wrapping", () => {
  it("converts a raw fetch failure into a ProblemError on get", async () => {
    const store = new CommunityStore(failingApi());

    await expect(store.get("test")).rejects.toMatchObject({ name: "ProblemError" });
  });

  it("converts a raw fetch failure into a ProblemError on create", async () => {
    const store = new CommunityStore(failingApi());

    await expect(store.create({ slug: "test", title: "Test" })).rejects.toMatchObject({ name: "ProblemError" });
  });

  it("converts a raw fetch failure into a ProblemError on update", async () => {
    const store = new CommunityStore(failingApi());

    await expect(store.update("test", { title: "Test" })).rejects.toMatchObject({ name: "ProblemError" });
  });

  it("converts a raw fetch failure into a ProblemError on remove", async () => {
    const store = new CommunityStore(failingApi());

    await expect(store.remove("test")).rejects.toMatchObject({ name: "ProblemError" });
  });
});
