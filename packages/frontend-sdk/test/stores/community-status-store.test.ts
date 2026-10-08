import { describe, expect, it } from "vitest";

import { CommunityStatusStore } from "../../src/stores/community-status-store.js";
import { failingApi, stubbedApi } from "../support/api.js";

const live = { state: "live" as const, revision: 3, running_revision: 3 };

describe("CommunityStatusStore", () => {
  it("loads a community's status", async () => {
    const { api, calls } = stubbedApi(() => ({ body: live }));
    const store = new CommunityStatusStore(api);

    await store.load("test");

    expect(store.status("test")).toEqual(live);
    expect(store.status("other")).toBeUndefined();
    expect(calls[0]!.path).toBe("/management/communities/test/status");
  });

  it("forgets the status it had when loading it again fails", async () => {
    let fail = false;
    const { api } = stubbedApi(() => (fail ? { status: 500, body: { status: 500 } } : { body: live }));
    const store = new CommunityStatusStore(api);
    await store.load("test");

    fail = true;
    await store.load("test");

    expect(store.status("test")).toBeUndefined();
    expect(store.error).toMatchObject({ name: "ProblemError", status: 500 });
  });

  it("converts a raw fetch failure into a ProblemError", async () => {
    const store = new CommunityStatusStore(failingApi());

    await store.load("test");

    expect(store.error).toMatchObject({ name: "ProblemError" });
  });
});
