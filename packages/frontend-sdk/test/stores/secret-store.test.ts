import { describe, expect, it } from "vitest";

import { SecretStore } from "../../src/stores/secret-store.js";
import { failingApi, stubbedApi } from "../support/api.js";

const key = { name: "entsoe_key", description: "ENTSO-E" };
const acc = { name: "acc", description: null };

describe("SecretStore", () => {
  it("loads a community's secrets", async () => {
    const { api, calls } = stubbedApi(() => ({ body: [key, acc] }));
    const store = new SecretStore(api);

    await store.load("test");

    expect(store.list("test")).toEqual([key, acc]);
    expect(store.find("test", "acc")).toEqual(acc);
    expect(calls[0]!.path).toBe("/management/communities/test/secrets");
  });

  it("creates a secret, appending what the server reported to a loaded cache", async () => {
    const { api, calls } = stubbedApi((call) => (call.method === "GET" ? { body: [key] } : { body: acc }));
    const store = new SecretStore(api);
    await store.load("test");

    await store.create("test", { name: "acc", value: "acc-credentials" });

    expect(calls[1]).toMatchObject({ method: "POST", body: { name: "acc", value: "acc-credentials" } });
    expect(store.list("test")).toEqual([key, acc]);
  });

  it("overwrites a secret's value", async () => {
    const updated = { ...key, description: "rotated" };
    const { api, calls } = stubbedApi((call) => (call.method === "GET" ? { body: [key] } : { body: updated }));
    const store = new SecretStore(api);
    await store.load("test");

    await store.replace("test", "entsoe_key", { name: "entsoe_key", description: "rotated", value: "new" });

    expect(calls[1]).toMatchObject({ method: "PUT", path: "/management/communities/test/secrets/entsoe_key" });
    expect(store.find("test", "entsoe_key")).toEqual(updated);
  });

  it("drops a removed secret from a loaded cache", async () => {
    const { api } = stubbedApi((call) => (call.method === "GET" ? { body: [key] } : { status: 204 }));
    const store = new SecretStore(api);
    await store.load("test");

    await store.remove("test", "entsoe_key");

    expect(store.list("test")).toEqual([]);
  });

  it("converts a raw fetch failure into a ProblemError on create", async () => {
    await expect(new SecretStore(failingApi()).create("test", { name: "a", value: "x" })).rejects.toMatchObject({
      name: "ProblemError",
    });
  });
});
