import { describe, expect, it } from "vitest";

import { ApiClient } from "../src/api-client.js";
import { ProblemError } from "../src/errors.js";
import { stubbedApi, ORIGIN } from "./support/api.js";
import { stubFetch } from "./support/stub-fetch.js";

const COLLECTION = "/management/communities" as const;
const ITEM = "/management/communities/{slug}" as const;

const community = { slug: "test", title: "Test", description: "", debug_mode: false, module_count: 1 };

describe("ApiClient", () => {
  it("resolves with the response body, not the fetch result", async () => {
    const { api } = stubbedApi(() => ({ body: [community] }));

    // no unwrapping at the call site: the body is what a caller gets
    expect(await api.GET(COLLECTION, {})).toEqual([community]);
  });

  it("fills path parameters", async () => {
    const { api, calls } = stubbedApi(() => ({ body: community }));

    await api.GET(ITEM, { params: { path: { slug: "test" } } });

    expect(calls[0]!.path).toBe("/management/communities/test");
  });

  it("sends a body on a write and returns what came back", async () => {
    const { api, calls } = stubbedApi((call) => ({ status: 201, body: call.body }));

    const created = await api.POST(COLLECTION, { body: { slug: "new", title: "New" } });

    expect(calls[0]).toMatchObject({ method: "POST", body: { slug: "new", title: "New" } });
    expect(created).toEqual({ slug: "new", title: "New" });
  });

  it("resolves with nothing for a delete", async () => {
    const { api } = stubbedApi(() => ({ status: 204 }));

    await expect(api.DELETE(ITEM, { params: { path: { slug: "test" } } })).resolves.toBeUndefined();
  });

  it("throws a ProblemError carrying the problem document", async () => {
    const problem = {
      title: "Unprocessable Content",
      status: 422,
      detail: "Request validation failed.",
      errors: [{ loc: ["body", "source", "api_key"], msg: "Field required", type: "missing" }],
    };
    const { api } = stubbedApi(() => ({ status: 422, body: problem, contentType: "application/problem+json" }));

    const error = (await api.GET(COLLECTION, {}).catch((e: unknown) => e)) as ProblemError;

    expect(error).toBeInstanceOf(ProblemError);
    expect(error.status).toBe(422);
    expect(error.message).toBe("Request validation failed.");
    expect(error.errors[0]!.loc).toEqual(["body", "source", "api_key"]);
  });

  it("throws on a failed delete too", async () => {
    const { api } = stubbedApi(() => ({ status: 404, body: { status: 404, detail: "gone" } }));

    await expect(api.DELETE(ITEM, { params: { path: { slug: "nope" } } })).rejects.toThrow("gone");
  });

  it("flags a 404 and a 409 for callers that treat them differently", async () => {
    const notFound = stubbedApi(() => ({ status: 404, body: { status: 404, detail: "gone" } }));
    const conflict = stubbedApi(() => ({ status: 409, body: { status: 409, detail: "exists" } }));

    const a = (await notFound.api.GET(COLLECTION, {}).catch((e: unknown) => e)) as ProblemError;
    const b = (await conflict.api.GET(COLLECTION, {}).catch((e: unknown) => e)) as ProblemError;

    expect(a.isNotFound).toBe(true);
    expect(b.isConflict).toBe(true);
  });

  it("still produces a usable error when the body is not a problem document", async () => {
    const { api } = stubbedApi(() => ({ status: 502, body: "<html>gateway</html>", contentType: "text/html" }));

    const error = (await api.GET(COLLECTION, {}).catch((e: unknown) => e)) as ProblemError;

    expect(error).toBeInstanceOf(ProblemError);
    expect(error.status).toBe(502);
  });

  it("sends configured headers, which is where auth will attach", async () => {
    const { fetch, calls } = stubFetch(() => ({ body: [] }));

    await new ApiClient({ fetch, baseUrl: ORIGIN, headers: { Authorization: "Bearer t" } }).GET(COLLECTION, {});

    expect(calls[0]!.headers["authorization"]).toBe("Bearer t");
  });

  it("prefixes requests with a configured base url", async () => {
    const { fetch, calls } = stubFetch(() => ({ body: [] }));

    await new ApiClient({ fetch, baseUrl: "http://api.example/base" }).GET(COLLECTION, {});

    expect(calls[0]!.path).toBe("/base/management/communities");
  });
});
