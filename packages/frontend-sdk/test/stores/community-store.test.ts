import { describe, expect, it } from "vitest";

import { CommunityStore } from "../../src/stores/community-store.js";
import { failingApi, stubbedApi } from "../support/api.js";

function community(slug: string, title = slug): {
  slug: string;
  title: string;
  module_count: number;
  revision: number;
  api_url: string;
} {
  return { slug, title, module_count: 0, revision: 1, api_url: `http://localhost/${slug}/` };
}

describe("CommunityStore", () => {
  it("lists the communities, without a scope", async () => {
    const { api, calls } = stubbedApi(() => ({ body: [community("test")] }));
    const store = new CommunityStore(api);

    await store.fetch();

    expect(store.all()).toEqual([community("test")]);
    expect(store.get("test")).toEqual(community("test"));
    expect(calls[0]!.path).toBe("/management/communities");
  });

  it("replaces a community in the listing with what the server stored", async () => {
    const { api, calls } = stubbedApi((call) =>
      call.method === "GET" ? { body: [community("test")] } : { body: community("test", "Renamed") },
    );
    const store = new CommunityStore(api);
    await store.fetch();

    await store.replace("test", { title: "Renamed" });

    expect(calls[1]).toMatchObject({ method: "PUT", path: "/management/communities/test" });
    expect(store.get("test")?.title).toBe("Renamed");
  });

  it("drops a deleted community from the listing", async () => {
    const { api } = stubbedApi((call) => (call.method === "GET" ? { body: [community("test")] } : { status: 204 }));
    const store = new CommunityStore(api);
    await store.fetch();

    await store.delete("test");

    expect(store.all()).toEqual([]);
  });

  it("converts a raw fetch failure into a ProblemError on a write", async () => {
    await expect(new CommunityStore(failingApi()).delete("test")).rejects.toMatchObject({ name: "ProblemError" });
  });
});
