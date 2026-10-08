import { describe, expect, it } from "vitest";

import { ApiClient } from "../../src/api-client.js";
import { Cache } from "../../src/core/cache.js";
import { ProblemError } from "../../src/errors.js";

interface Request {
  slug: string;
  resolve: (value: string) => void;
  reject: (error: unknown) => void;
}

/** A cache whose requests stay open until the test answers them, in order. */
class Controlled extends Cache<[slug: string], string> {
  public readonly requests: Request[] = [];
  protected readonly path = "/management/communities/{slug}/status";

  public get(slug: string): string | undefined {
    return this.read(slug);
  }

  public change(slug: string, change: (value: string) => string): void {
    this.update([slug], change);
  }

  protected override request(slug: string): Promise<string> {
    return new Promise<string>((resolve, reject) => this.requests.push({ slug, resolve, reject }));
  }
}

function controlled(): { cache: Controlled; requests: Request[] } {
  const cache = new Controlled(new ApiClient());
  return { cache, requests: cache.requests };
}

/** Let answered requests settle. */
async function flush(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
}

describe("Cache", () => {
  it("starts fetching when read, and answers once it has", async () => {
    const { cache, requests } = controlled();

    expect(cache.get("a")).toBeUndefined();
    expect(requests.map((request) => request.slug)).toEqual(["a"]);

    requests[0]!.resolve("A");
    await flush();

    expect(cache.get("a")).toBe("A");
    expect(requests).toHaveLength(1);
  });

  it("shares one request between every read and fetch while it is under way", async () => {
    const { cache, requests } = controlled();

    cache.get("a");
    cache.get("a");
    const fetched = cache.fetch("a");
    requests[0]!.resolve("A");

    await expect(fetched).resolves.toBe("A");
    expect(requests).toHaveLength(1);
  });

  it("keeps scopes apart", async () => {
    const { cache, requests } = controlled();

    cache.get("a");
    cache.get("b");
    requests[0]!.resolve("A");
    requests[1]!.resolve("B");
    await flush();

    expect([cache.get("a"), cache.get("b")]).toEqual(["A", "B"]);
  });

  it("keeps showing an invalidated value while fetching it again on the next read", async () => {
    const { cache, requests } = controlled();
    cache.get("a");
    requests[0]!.resolve("A");
    await flush();

    cache.invalidate("a");
    expect(requests).toHaveLength(1);

    expect(cache.get("a")).toBe("A");
    requests[1]!.resolve("A2");
    await flush();

    expect(cache.get("a")).toBe("A2");
  });

  it("does not trust an answer to a request invalidated while it was under way", async () => {
    const { cache, requests } = controlled();
    cache.get("a");

    cache.invalidate("a");
    requests[0]!.resolve("old");
    await flush();

    // Shown, but stale: reading it asks again.
    expect(cache.get("a")).toBe("old");
    expect(requests).toHaveLength(2);
  });

  it("lets a newer request win over one it replaced", async () => {
    const { cache, requests } = controlled();
    cache.get("a");
    cache.invalidate("a");
    cache.get("a");

    requests[1]!.resolve("new");
    requests[0]!.resolve("old");
    await flush();

    expect(cache.get("a")).toBe("new");
    expect(requests).toHaveLength(2);
  });

  it("records a failure as a ProblemError, keeping the last value, without retrying on read", async () => {
    const { cache, requests } = controlled();
    cache.get("a");
    requests[0]!.resolve("A");
    await flush();

    cache.invalidate("a");
    cache.get("a");
    requests[1]!.reject(new TypeError("network error"));
    await flush();

    expect(cache.error("a")).toBeInstanceOf(ProblemError);
    expect(cache.get("a")).toBe("A");
    expect(requests).toHaveLength(2);
  });

  it("rejects a fetch with a ProblemError", async () => {
    const { cache, requests } = controlled();
    const fetched = cache.fetch("a");

    requests[0]!.reject(new TypeError("network error"));

    await expect(fetched).rejects.toBeInstanceOf(ProblemError);
  });

  it("clears the failure once a fetch succeeds", async () => {
    const { cache, requests } = controlled();
    cache.fetch("a").catch(() => {});
    requests[0]!.reject(new TypeError("network error"));
    await flush();

    cache.invalidate("a");
    cache.get("a");
    requests[1]!.resolve("A");
    await flush();

    expect(cache.error("a")).toBeNull();
  });

  it("forgets a scope entirely", async () => {
    const { cache, requests } = controlled();
    cache.get("a");
    requests[0]!.resolve("A");
    await flush();

    cache.forget("a");

    expect(cache.get("a")).toBeUndefined();
    expect(requests).toHaveLength(2);
  });

  it("only updates a value that is loaded", async () => {
    const { cache, requests } = controlled();

    cache.change("a", (value) => `${value}!`);
    expect(cache.get("a")).toBeUndefined();

    requests[0]!.resolve("A");
    await flush();
    cache.change("a", (value) => `${value}!`);

    expect(cache.get("a")).toBe("A!");
  });
});
