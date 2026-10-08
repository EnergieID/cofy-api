import { describe, expect, it } from "vitest";

import { CommunityStatusStore } from "../../src/stores/community-status-store.js";
import { failingApi, stubbedApi } from "../support/api.js";

const live = { state: "live" as const, revision: 3, running_revision: 3 };

describe("CommunityStatusStore", () => {
  it("loads a community's status", async () => {
    const { api, calls } = stubbedApi(() => ({ body: live }));
    const store = new CommunityStatusStore(api);

    await store.fetch("test");

    expect(store.get("test")).toEqual(live);
    expect(calls[0]!.path).toBe("/management/communities/test/status");
  });

  it("converts a raw fetch failure into a ProblemError", async () => {
    const store = new CommunityStatusStore(failingApi());

    await store.fetch("test").catch(() => {});

    expect(store.error("test")).toMatchObject({ name: "ProblemError" });
  });
});
