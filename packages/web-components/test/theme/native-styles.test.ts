import { describe, expect, it } from "vitest";

import { nativeStyles } from "../../src/theme/native-styles.js";
import { layoutStyles } from "../../src/theme/layout-styles.js";

/**
 * Both of these come from a `?raw` import of a file in the installed `@awesome.me/webawesome`.
 * Vitest's default `css: false` silently resolves that to an empty string rather than failing -
 * these tests exist to catch a regression of that setting, not just to check the content.
 */
describe("nativeStyles", () => {
  it("carries the real stylesheet, not an empty stub", () => {
    expect(nativeStyles.cssText.length).toBeGreaterThan(10_000);
  });

  it("supplies the box-sizing anchor a shadow root does not otherwise have", () => {
    expect(nativeStyles.cssText).toContain(":host {\n  box-sizing: border-box;\n}");
  });

  it("strips the @imports a document stylesheet needs but an adopted one cannot resolve", () => {
    expect(nativeStyles.cssText).not.toContain("@import");
  });

  it("still carries the rules those @imports sat above", () => {
    expect(nativeStyles.cssText).toContain("@layer wa-native");
    expect(nativeStyles.cssText).toContain("font-size: var(--wa-font-size-2xl)");
  });
});

describe("layoutStyles", () => {
  it("carries the real stylesheet, not an empty stub", () => {
    expect(layoutStyles.cssText.length).toBeGreaterThan(1_000);
  });

  it("declares the layout classes our components render", () => {
    expect(layoutStyles.cssText).toContain("wa-cluster");
    expect(layoutStyles.cssText).toContain("wa-split");
  });
});
