/**
 * Reads the theme's source off disk, so this one runs in node rather than the jsdom default.
 *
 * @vitest-environment node
 */
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

// CodeMirror turns its style specs into a `StyleModule` that only a live `EditorView`
// assembles, so the token names are read from the source rather than from the extension. What
// is being checked is exactly a textual claim: which custom properties this file names.
const source = readFileSync(new URL("../../src/components/editor/yaml-highlight.ts", import.meta.url), "utf8");
const syntaxCss = readFileSync(new URL("../../src/theme/syntax.css", import.meta.url), "utf8");
const waTheme = readFileSync(
  new URL("../../node_modules/@awesome.me/webawesome/dist/styles/themes/default.css", import.meta.url),
  "utf8",
);
const waPalette = readFileSync(
  new URL("../../node_modules/@awesome.me/webawesome/dist/styles/color/palettes/default.css", import.meta.url),
  "utf8",
);

const named = (text: string): string[] => [
  ...new Set([...text.matchAll(/var\((--[a-z0-9-]+)/g)].map((match) => match[1]!)),
];

const used = named(source);

/** The custom properties declared inside one block of the syntax stylesheet. */
function declaredIn(selector: string): string[] {
  const start = syntaxCss.indexOf(selector);
  const block = syntaxCss.slice(syntaxCss.indexOf("{", start) + 1, syntaxCss.indexOf("}", start));
  return [...block.matchAll(/(--[a-z0-9-]+)\s*:/g)].map((match) => match[1]!);
}

describe("cofyEditorTheme", () => {
  it("drives every colour from a token, so a scheme change needs no rebuild", () => {
    // Custom properties inherit through shadow roots, so the editor follows the document on its
    // own. A literal colour here would be the one thing that does not.
    expect([...source.matchAll(/#[0-9a-fA-F]{3,8}\b/g)]).toEqual([]);
    expect(used.length).toBeGreaterThan(10);
  });

  it("names only Web Awesome tokens that actually exist", () => {
    const declared = new Set(
      [...`${waTheme}${waPalette}`.matchAll(/(--wa-[a-z0-9-]+)\s*:/g)].map((match) => match[1]!),
    );
    const unknown = used.filter((token) => token.startsWith("--wa-") && !declared.has(token));

    expect(unknown).toEqual([]);
  });

  it("gives every syntax token a light and a dark value", () => {
    // This is the whole reason the stylesheet exists. Web Awesome's hue tints are absolute -
    // `--wa-color-indigo-40` is the same colour in both schemes - so a syntax colour that is
    // legible on white is not legible on black unless a different tint is chosen for it.
    const light = declaredIn(":root,");
    const dark = declaredIn(".wa-dark");

    expect(light).toEqual(dark);
    expect(light.length).toBe(8);
  });

  it("declares every syntax token the editor asks for, and none it does not", () => {
    const asked = used.filter((token) => token.startsWith("--cofy-syntax-")).sort();

    expect(declaredIn(":root,").sort()).toEqual(asked);
  });

  it("falls back to a real colour for every syntax token, so the stylesheet stays optional", () => {
    // A deployment that does not import `syntax.css` still gets a coloured editor in light mode.
    const withoutFallback = [...source.matchAll(/var\((--cofy-syntax-[a-z-]+)\)/g)];

    expect(withoutFallback).toEqual([]);
  });
});
