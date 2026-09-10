import { describe, expect, it } from "vitest";
import { html } from "lit";
import type { TemplateResult } from "lit";

import { buildHash, buildPath, matchRoute, pathFromHash, type RouteTable } from "../src/router.js";

const routes = {
  communities: { path: "/", render: (): TemplateResult => html`root` },
  modules: { path: "/c/:slug", render: (): TemplateResult => html`modules` },
  newModule: { path: "/c/:slug/new", render: (): TemplateResult => html`new` },
  module: { path: "/c/:slug/:type/:name", render: (): TemplateResult => html`module` },
} satisfies RouteTable;

describe("matchRoute", () => {
  it.each([
    ["/", "communities", {}],
    ["/c/foo", "modules", { slug: "foo" }],
    ["/c/foo/new", "newModule", { slug: "foo" }],
    ["/c/foo/tariff/spot", "module", { slug: "foo", type: "tariff", name: "spot" }],
  ])("matches %s to the %s route", (path, name, params) => {
    const match = matchRoute(routes, path)!;

    expect(match.name).toBe(name);
    expect(match.params).toEqual(params);
  });

  it("prefers a literal segment over a parameter that would also match", () => {
    // `/c/foo/new` must be the create page, never a module named "new"
    expect(matchRoute(routes, "/c/foo/new")!.name).toBe("newModule");
  });

  it("does not match a path with the wrong number of segments", () => {
    expect(matchRoute(routes, "/c")).toBeUndefined();
    expect(matchRoute(routes, "/c/foo/tariff/spot/extra")).toBeUndefined();
  });

  it("returns nothing when no route claims the path", () => {
    expect(matchRoute(routes, "/nope")).toBeUndefined();
  });

  it("decodes captured segments", () => {
    expect(matchRoute(routes, "/c/a%2Fb")!.params["slug"]).toBe("a/b");
  });

  it("ignores a trailing slash", () => {
    expect(matchRoute(routes, "/c/foo/")!.name).toBe("modules");
  });
});

describe("buildPath", () => {
  it("fills parameters", () => {
    expect(buildPath("/c/:slug/:type/:name", { slug: "foo", type: "tariff", name: "spot" })).toBe(
      "/c/foo/tariff/spot",
    );
  });

  it("encodes a value that would otherwise add a segment", () => {
    expect(buildPath("/c/:slug", { slug: "a/b" })).toBe("/c/a%2Fb");
  });

  it("round trips through matchRoute", () => {
    const params = { slug: "a/b", type: "tariff", name: "spot" };

    const match = matchRoute(routes, buildPath("/c/:slug/:type/:name", params))!;

    expect(match.params).toEqual(params);
  });

  it("refuses a pattern it cannot fill, rather than producing a broken link", () => {
    expect(() => buildPath("/c/:slug", {})).toThrow("Missing route parameter");
  });

  it("builds the root path", () => {
    expect(buildPath("/")).toBe("/");
  });
});

describe("hashes", () => {
  it("prefixes a built path", () => {
    expect(buildHash("/c/:slug", { slug: "foo" })).toBe("#/c/foo");
  });

  it.each([
    ["#/c/foo", "/c/foo"],
    ["#/", "/"],
    ["", "/"],
  ])("reads %s as %s", (hash, path) => {
    expect(pathFromHash(hash)).toBe(path);
  });
});
