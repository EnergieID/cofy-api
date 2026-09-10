import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { html } from "lit";
import type { TemplateResult } from "lit";

import { RouteState } from "../../src/states/route-state.js";
import type { RouteTable } from "../../src/router.js";

const routes = {
  communities: { path: "/", render: (): TemplateResult => html`<p>root</p>` },
  modules: { path: "/c/:slug", render: ({ slug }): TemplateResult => html`<p>modules ${slug}</p>` },
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
    window.location.hash = "#/c/foo";

    expect(new RouteState(routes).path).toBe("/c/foo");
  });

  it("defaults to the root path", () => {
    expect(state.path).toBe("/");
  });

  it("writes the hash when navigating, so the address bar and back button agree", () => {
    state.navigate("modules", { slug: "foo" });

    expect(window.location.hash).toBe("#/c/foo");
    expect(state.path).toBe("/c/foo");
  });

  it("updates state even when the hash is already what it would set", () => {
    // `hashchange` does not fire for a no-op assignment, so the state cannot wait for it
    window.location.hash = "#/c/foo";
    state.navigate("modules", { slug: "foo" });

    expect(state.path).toBe("/c/foo");
  });

  it("follows the address bar changing underneath it", async () => {
    window.location.hash = "#/c/bar";
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(state.path).toBe("/c/bar");
  });

  it("stops following once stopped", async () => {
    state.stop();
    window.location.hash = "#/c/bar";
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
    expect(state.hashFor("modules", { slug: "foo" })).toBe("#/c/foo");
  });

  it("renders the matching route with its parameters", () => {
    state.navigate("modules", { slug: "foo" });

    expect(JSON.stringify(state.render().values)).toContain("foo");
  });

  it("says so when no route claims the path", () => {
    window.location.hash = "#/nope";
    const orphan = new RouteState(routes);

    expect(JSON.stringify(orphan.render().values)).toContain("/nope");
  });
});
