import { describe, expect, it } from "vitest";

import { matchRoute } from "../src/router.js";
import { routes } from "../src/routes.js";

describe("routes", () => {
  it.each([
    ["/communities/foo", "modules", { slug: "foo" }],
    ["/communities/foo/resources", "resources", { slug: "foo" }],
    ["/communities/foo/secrets", "secrets", { slug: "foo" }],
    ["/communities/foo/tokens", "tokens", { slug: "foo" }],
    ["/communities/foo/resources/new", "newResource", { slug: "foo" }],
    ["/communities/foo/resources/entsoe_key", "resource", { slug: "foo", name: "entsoe_key" }],
    ["/communities/foo/modules/tariff/spot", "module", { slug: "foo", type: "tariff", name: "spot" }],
  ])("matches %s to the %s page", (path, name, params) => {
    const match = matchRoute(routes, path)!;

    expect(match.name).toBe(name);
    expect(match.params).toEqual(params);
  });
});
