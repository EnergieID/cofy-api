import { beforeEach, describe, expect, it, vi } from "vitest";

import { COLOR_SCHEMES, ThemeState } from "../../src/theme/theme-state.js";

function memoryStorage(initial?: string): Pick<Storage, "getItem" | "setItem"> {
  const values = new Map<string, string>(initial === undefined ? [] : [["cofy.theme", initial]]);
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => void values.set(key, value),
  };
}

/**
 * A stand-in for the system preference that a test can flip.
 *
 * Real enough to be subscribed to and unsubscribed from, which is what the "follows the system"
 * behaviour is made of - a bare `{ matches }` would pass the startup assertions and prove
 * nothing about the rest.
 */
function fakeMedia(matches = false): MediaQueryList & { emit: (dark: boolean) => void; listeners: number } {
  const listeners = new Set<(event: MediaQueryListEvent) => void>();
  const media = {
    matches,
    addEventListener: (_: string, handler: (event: MediaQueryListEvent) => void): void => void listeners.add(handler),
    removeEventListener: (_: string, handler: (event: MediaQueryListEvent) => void): void =>
      void listeners.delete(handler),
    get listeners(): number {
      return listeners.size;
    },
    emit(dark: boolean): void {
      media.matches = dark;
      for (const handler of listeners) handler({ matches: dark } as MediaQueryListEvent);
    },
  };
  return media as unknown as MediaQueryList & { emit: (dark: boolean) => void; listeners: number };
}

/** What Web Awesome actually keys its two colour schemes off. */
function appliedScheme(): string {
  const { classList } = document.documentElement;
  return classList.contains("wa-dark") ? "dark" : classList.contains("wa-light") ? "light" : "none";
}

describe("ThemeState", () => {
  beforeEach(() => {
    document.documentElement.classList.remove("wa-dark", "wa-light");
    vi.restoreAllMocks();
  });

  it("defers to the system by default", () => {
    const state = new ThemeState({ storage: memoryStorage(), media: fakeMedia(true) });

    expect(state.scheme).toBe("system");
    expect(state.resolved).toBe("dark");
  });

  it("resolves to light where the system asks for light", () => {
    const state = new ThemeState({ storage: memoryStorage(), media: fakeMedia(false) });

    expect(state.resolved).toBe("light");
  });

  it("prefers a remembered choice over the system", () => {
    const state = new ThemeState({ storage: memoryStorage("light"), media: fakeMedia(true) });

    expect(state.scheme).toBe("light");
    expect(state.resolved).toBe("light");
  });

  it("ignores a remembered value that is not a scheme", () => {
    // A console upgraded from the Carbon themes has "g100" or "white" sitting in storage.
    const state = new ThemeState({ storage: memoryStorage("g100"), media: fakeMedia(false) });

    expect(state.scheme).toBe("system");
  });

  it("puts the scheme on the document, which is what the theme switches on", () => {
    const state = new ThemeState({ storage: memoryStorage(), media: fakeMedia(false) });
    state.start();
    expect(appliedScheme()).toBe("light");

    state.select("dark");

    expect(appliedScheme()).toBe("dark");
    state.stop();
  });

  it("remembers the choice", () => {
    const storage = memoryStorage();
    const state = new ThemeState({ storage, media: fakeMedia(false) });

    state.select("dark");

    expect(storage.getItem("cofy.theme")).toBe("dark");
  });

  it("notifies subscribers, so a picker re-renders", () => {
    const state = new ThemeState({ storage: memoryStorage(), media: fakeMedia(false) });
    const seen: string[] = [];
    state.subscribe(() => seen.push(state.scheme));

    state.select("dark");

    expect(seen).toEqual(["dark"]);
  });

  it("works where localStorage throws", () => {
    vi.spyOn(globalThis.localStorage, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });

    expect(() => new ThemeState({ media: fakeMedia(false) }).select("dark")).not.toThrow();
  });

  it("offers exactly the three choices a picker renders", () => {
    expect([...COLOR_SCHEMES]).toEqual(["system", "light", "dark"]);
  });
});

describe("ThemeState following the system", () => {
  beforeEach(() => {
    document.documentElement.classList.remove("wa-dark", "wa-light");
  });

  it("keeps following the system after the page has loaded", () => {
    // The point of "System" being a choice rather than a one-off reading: the reader switches
    // their OS to dark at sunset and the console follows without a reload.
    const media = fakeMedia(false);
    const state = new ThemeState({ storage: memoryStorage(), media });
    state.start();
    expect(appliedScheme()).toBe("light");

    media.emit(true);

    expect(appliedScheme()).toBe("dark");
    // The appearance changed; the *choice* did not.
    expect(state.scheme).toBe("system");
    expect(state.resolved).toBe("dark");
    state.stop();
  });

  it("stops following once an explicit choice is made", () => {
    const media = fakeMedia(false);
    const state = new ThemeState({ storage: memoryStorage(), media });
    state.start();

    state.select("light");
    media.emit(true);

    expect(appliedScheme()).toBe("light");
    state.stop();
  });

  it("lets go of the system listener when stopped", () => {
    const media = fakeMedia(false);
    const state = new ThemeState({ storage: memoryStorage(), media });

    state.start();
    expect(media.listeners).toBe(1);
    state.stop();

    expect(media.listeners).toBe(0);
  });

  it("does not need a system preference to exist at all", () => {
    // Some embedding contexts have no `matchMedia`.
    const state = new ThemeState({ storage: memoryStorage(), media: null });
    state.start();

    expect(appliedScheme()).toBe("light");
    expect(() => state.stop()).not.toThrow();
  });
});
