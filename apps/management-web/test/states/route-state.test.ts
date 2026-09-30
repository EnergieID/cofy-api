import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { html } from "lit";
import type { TemplateResult } from "lit";

import { RouteState } from "../../src/states/route-state.js";
import type { RouteTable } from "../../src/router.js";

const routes = {
  communities: { path: "/", render: (): TemplateResult => html`<p>root</p>` },
  modules: { path: "/communities/:slug", render: ({ slug }): TemplateResult => html`<p>modules ${slug}</p>` },
} satisfies RouteTable;

describe("RouteState", () => {
  let state: RouteState;

  beforeEach(() => {
    window.location.hash = "";
    state = new RouteState(routes);
    state.start();
  });

  afterEach(() => {
    state.stop();
  });

  it("starts from the address bar", () => {
    window.location.hash = "#/communities/foo";

    expect(new RouteState(routes).path).toBe("/communities/foo");
  });

  it("defaults to the root path", () => {
    expect(state.path).toBe("/");
  });

  it("writes the hash when navigating, so the address bar and back button agree", () => {
    state.navigate("modules", { slug: "foo" });

    expect(window.location.hash).toBe("#/communities/foo");
    expect(state.path).toBe("/communities/foo");
  });

  it("updates state even when the hash is already what it would set", () => {
    // `hashchange` does not fire for a no-op assignment, so the state cannot wait for it
    window.location.hash = "#/communities/foo";
    state.navigate("modules", { slug: "foo" });

    expect(state.path).toBe("/communities/foo");
  });

  it("follows the address bar changing underneath it", async () => {
    window.location.hash = "#/communities/bar";
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(state.path).toBe("/communities/bar");
  });

  it("stops following once stopped", async () => {
    state.stop();
    window.location.hash = "#/communities/bar";
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(state.path).toBe("/");
  });

  it("notifies subscribers when the path changes", () => {
    const seen: (string | undefined)[] = [];
    state.subscribe((_s, key) => seen.push(key));

    state.navigate("modules", { slug: "foo" });

    expect(seen).toContain("path");
  });

  it("builds a hash for a named route, so a link never spells out a path", () => {
    expect(state.hashFor("modules", { slug: "foo" })).toBe("#/communities/foo");
  });

  it("renders the matching route with its parameters", () => {
    state.navigate("modules", { slug: "foo" });

    expect(JSON.stringify(state.render()!.values)).toContain("foo");
  });

  it("says so when no route claims the path", () => {
    window.location.hash = "#/nope";
    const orphan = new RouteState(routes);

    expect(orphan.render()).toBeUndefined();
  });
});
