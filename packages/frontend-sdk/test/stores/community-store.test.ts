import { describe, expect, it } from "vitest";

import { CommunityStore } from "../../src/stores/community-store.js";
import { stubbedApi } from "../support/api.js";

const community = { slug: "test", title: "Test", description: "", debug_mode: false, module_count: 1 };

describe("CommunityStore", () => {
  it("loads the listing the server returns", async () => {
    const { api } = stubbedApi(() => ({ body: [community] }));
    const store = new CommunityStore(api);

    await store.load();

    expect(store.communities).toEqual([community]);
    expect(store.loaded).toBe(true);
    expect(store.loading).toBe(false);
  });

  it("captures a failure instead of throwing, so the shell can render it", async () => {
    const { api } = stubbedApi(() => ({ status: 500, body: { status: 500, detail: "boom" } }));
    const store = new CommunityStore(api);

    await store.load();

    expect(store.error?.status).toBe(500);
    expect(store.loading).toBe(false);
  });

  it("resolves the selected community", async () => {
    const { api } = stubbedApi(() => ({ body: [community] }));
    const store = new CommunityStore(api);
    await store.load();

    store.select("test");

    expect(store.current).toEqual(community);
  });

  it("keeps the listing sorted when one is created", async () => {
    const created = { ...community, slug: "aaa", title: "A" };
    const { api } = stubbedApi((call) =>
      call.method === "POST" ? { status: 201, body: created } : { body: [community] },
    );
    const store = new CommunityStore(api);
    await store.load();

    await store.create({ slug: "aaa", title: "A" });

    expect(store.communities.map((c) => c.slug)).toEqual(["aaa", "test"]);
  });

  it("swaps an updated community in place", async () => {
    const renamed = { ...community, title: "Renamed" };
    const { api } = stubbedApi((call) => (call.method === "PUT" ? { body: renamed } : { body: [community] }));
    const store = new CommunityStore(api);
    await store.load();

    await store.update("test", { title: "Renamed" });

    expect(store.communities).toEqual([renamed]);
  });

  it("clears the selection when the selected community is deleted", async () => {
    const { api } = stubbedApi((call) => (call.method === "DELETE" ? { status: 204 } : { body: [community] }));
    const store = new CommunityStore(api);
    await store.load();
    store.select("test");

    await store.remove("test");

    expect(store.communities).toEqual([]);
    expect(store.currentSlug).toBeNull();
  });

  it("addresses one community by slug", async () => {
    const { api, calls } = stubbedApi(() => ({ body: community }));
    const store = new CommunityStore(api);

    await store.get("test");

    expect(calls[0]!.path).toBe("/management/communities/test");
  });

  it("notifies subscribers when the listing changes", async () => {
    const { api } = stubbedApi(() => ({ body: [community] }));
    const store = new CommunityStore(api);
    const seen: (string | undefined)[] = [];
    store.subscribe((_s, key) => seen.push(key));

    await store.load();

    expect(seen).toContain("communities");
  });
});
