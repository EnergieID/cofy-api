import { describe, expect, it } from "vitest";

import { nativeStyles } from "../../src/theme/native-styles.js";
import { utilityStyles } from "../../src/theme/utility-styles.js";

/**
 * Both of these resolve a real stylesheet from the installed `@awesome.me/webawesome` through
 * Vite's `?inline` CSS handling. Vitest's default `css: false` silently resolves that to an
 * empty string rather than failing - these tests exist to catch a regression of that setting,
 * not just to check the content.
 */
describe("nativeStyles", () => {
  it("carries the real stylesheet, not an empty stub", () => {
    expect(nativeStyles.cssText.length).toBeGreaterThan(10_000);
  });

  it("supplies the box-sizing anchor a shadow root does not otherwise have", () => {
    expect(nativeStyles.cssText).toContain(":host {\n  box-sizing: border-box;\n}");
  });

  it("resolves its own @imports rather than leaving them for an adopted stylesheet to fail on", () => {
    expect(nativeStyles.cssText).not.toContain("@import");
  });

  it("carries what those @imports resolve to - cascade layer order, native element rules, colour variants and sizing", () => {
    expect(nativeStyles.cssText).toContain("@layer wa-native");
    expect(nativeStyles.cssText).toContain("font-size: var(--wa-font-size-2xl)");
    expect(nativeStyles.cssText).toContain(".wa-size-xs");
  });
});

describe("utilityStyles", () => {
  it("carries the real stylesheet, not an empty stub", () => {
    expect(utilityStyles.cssText.length).toBeGreaterThan(10_000);
  });

  it("resolves its own @imports rather than leaving them for an adopted stylesheet to fail on", () => {
    expect(utilityStyles.cssText).not.toContain("@import");
  });

  it("declares the utility classes our components render", () => {
    expect(utilityStyles.cssText).toContain("wa-cluster");
    expect(utilityStyles.cssText).toContain("wa-split");
    expect(utilityStyles.cssText).toContain("wa-gap-");
    expect(utilityStyles.cssText).toContain("wa-caption-");
    expect(utilityStyles.cssText).toContain("wa-form-control-label");
  });
});
