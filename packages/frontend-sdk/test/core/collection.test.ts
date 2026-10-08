import { describe, expect, it } from "vitest";

import type { ApiClient } from "../../src/api-client.js";
import { Collection, type Change } from "../../src/core/collection.js";
import { failingApi, stubbedApi } from "../support/api.js";
import type { Call } from "../support/stub-fetch.js";

interface Item {
  name: string;
  value: number;
}

/** Items per slug, at paths that follow the API's conventions. */
class Items extends Collection<[slug: string], Item, string, Item> {
  public readonly changes: Change<[slug: string], string>[];
  protected readonly path = "/management/communities/{slug}/secrets";
  protected readonly itemPath = "/management/communities/{slug}/secrets/{name}";

  public constructor(api: ApiClient) {
    const changes: Change<[slug: string], string>[] = [];
    super(api, (change) => changes.push(change));
    this.changes = changes;
  }

  protected idOf(item: Item): string {
    return item.name;
  }
}

/** *Items* against a server holding *server* per slug, which stores ten times the value it is sent. */
function items(server: Record<string, Item[]>): { items: Items; calls: Call[] } {
  const { api, calls } = stubbedApi((call) => {
    if (call.method === "GET") return { body: server[call.path.split("/")[3]!] ?? [] };
    if (call.method === "DELETE") return { status: 204 };
    const item = call.body as Item;
    return { body: { ...item, value: item.value * 10 } };
  });
  return { items: new Items(api), calls };
}

describe("Collection", () => {
  it("lists, creates, replaces and deletes at its path and its item path", async () => {
    const { items: store, calls } = items({ a: [{ name: "x", value: 1 }] });

    await store.fetch("a");
    await store.create("a", { name: "y", value: 2 });
    await store.replace("a", "x", { name: "x", value: 3 });
    await store.delete("a", "x");

    expect(calls.map((call) => `${call.method} ${call.path}`)).toEqual([
      "GET /management/communities/a/secrets",
      "POST /management/communities/a/secrets",
      "PUT /management/communities/a/secrets/x",
      "DELETE /management/communities/a/secrets/x",
    ]);
    expect(calls[1]!.body).toEqual({ name: "y", value: 2 });
    expect(calls[2]!.body).toEqual({ name: "x", value: 3 });
  });

  it("finds an item in the loaded list", async () => {
    const { items: store } = items({ a: [{ name: "x", value: 1 }] });

    expect(store.get("a", "x")).toBeUndefined();
    await store.fetch("a");

    expect(store.get("a", "x")).toEqual({ name: "x", value: 1 });
    expect(store.get("a", "y")).toBeUndefined();
  });

  it("caches what the server returned for a write", async () => {
    const { items: store } = items({ a: [{ name: "x", value: 1 }] });
    await store.fetch("a");

    await store.create("a", { name: "y", value: 2 });
    await store.replace("a", "x", { name: "x", value: 3 });

    expect(store.all("a")).toEqual([
      { name: "x", value: 30 },
      { name: "y", value: 20 },
    ]);

    await store.delete("a", "x");

    expect(store.all("a")).toEqual([{ name: "y", value: 20 }]);
  });

  it("does not cache a write to a scope that was never loaded", async () => {
    const { items: store } = items({});

    await store.create("a", { name: "y", value: 2 });

    // A cache of just the created item would pass for the whole list.
    expect(store.all("a")).toBeUndefined();
  });

  it("reports every write with its scope and identity", async () => {
    const { items: store } = items({});

    await store.create("a", { name: "y", value: 2 });
    await store.replace("a", "y", { name: "y", value: 3 });
    await store.delete("a", "y");

    expect(store.changes).toEqual([
      { action: "create", scope: ["a"], id: "y" },
      { action: "replace", scope: ["a"], id: "y" },
      { action: "delete", scope: ["a"], id: "y" },
    ]);
  });

  it("reports nothing for a write that failed", async () => {
    const store = new Items(failingApi());

    await expect(store.create("a", { name: "y", value: 2 })).rejects.toMatchObject({ name: "ProblemError" });
    expect(store.changes).toEqual([]);
  });
});
