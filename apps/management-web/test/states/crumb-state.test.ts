import { describe, expect, it } from "vitest";

import { CrumbState } from "../../src/states/crumb-state.js";

describe("CrumbState", () => {
  it("starts empty", () => {
    expect(new CrumbState().crumbs).toEqual([]);
  });

  it("holds what a page sets", () => {
    const state = new CrumbState();

    state.set([{ label: "Foo", href: "#/c/foo" }, { label: "spot" }]);

    expect(state.crumbs).toEqual([{ label: "Foo", href: "#/c/foo" }, { label: "spot" }]);
  });

  it("notifies subscribers on a real change", () => {
    const state = new CrumbState();
    const seen: (string | undefined)[] = [];
    state.subscribe((_s, key) => seen.push(key));

    state.set([{ label: "Foo" }]);

    expect(seen).toEqual(["crumbs"]);
  });

  it("stays quiet when set to the same trail", () => {
    // pages set the trail on every update; re-notifying would re-render the header each time
    const state = new CrumbState();
    state.set([{ label: "Foo" }]);
    const seen: (string | undefined)[] = [];
    state.subscribe((_s, key) => seen.push(key));

    state.set([{ label: "Foo" }]);

    expect(seen).toEqual([]);
  });

  it("clears back to empty", () => {
    const state = new CrumbState();
    state.set([{ label: "Foo" }]);

    state.clear();

    expect(state.crumbs).toEqual([]);
  });
});
