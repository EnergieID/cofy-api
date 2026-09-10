/**
 * Reads Carbon's stylesheet off disk to check these derivations against it, so this one runs
 * in node rather than the jsdom default the route tests need.
 *
 * @vitest-environment node
 */
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { white } from "@carbon/themes";

import { carbonThemeCss, layerOneTokens, spacingCss, tokenToCssName } from "../src/theme.js";

/** Carbon's own stylesheet, the authority these derivations are checked against. */
const carbonCss = readFileSync(
  new URL("../node_modules/@carbon/styles/css/styles.css", import.meta.url),
  "utf8",
);

describe("tokenToCssName", () => {
  it.each([
    ["layer01", "layer-01"],
    ["textPrimary", "text-primary"],
    ["borderSubtle00", "border-subtle-00"],
    ["layerSelectedHover01", "layer-selected-hover-01"],
    ["background", "background"],
  ])("maps %s to %s", (token, expected) => {
    expect(tokenToCssName(token)).toBe(expected);
  });

  it("produces a name Carbon actually declares, for every theme token", () => {
    const declared = new Set([...carbonCss.matchAll(/--cds-([a-z0-9-]+)\s*:/g)].map((match) => match[1]));
    const names = Object.entries(white)
      .filter(([, value]) => typeof value === "string")
      .map(([name]) => tokenToCssName(name));

    expect(names.filter((name) => !declared.has(name))).toEqual([]);
    expect(names.length).toBeGreaterThan(200);
  });
});

describe("layerOneTokens", () => {
  it("matches the contextual tokens Carbon declares for the outermost layer", () => {
    const start = carbonCss.indexOf(".cds--layer-one");
    const block = carbonCss.slice(carbonCss.indexOf("{", start) + 1, carbonCss.indexOf("}", start));

    const fromCarbon = Object.fromEntries(
      block
        .split(";")
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => {
          const [name, value] = line.split(":");
          const source = /var\(--cds-([a-z0-9-]+)/.exec(value!)![1]!;
          return [name!.trim().replace("--cds-", ""), source];
        }),
    );

    const ours = Object.fromEntries(
      Object.entries(layerOneTokens()).map(([name, source]) => [name, tokenToCssName(source)]),
    );

    expect(ours).toEqual(fromCarbon);
  });
});

describe("spacingCss", () => {
  it("declares the spacing scale Carbon's own stylesheet does", () => {
    // These come from `@carbon/layout`, not `@carbon/themes`, so they are easy to miss - and
    // a rule using one silently falls back to nothing when they are absent.
    const declared: Record<string, string> = Object.fromEntries(
      [...carbonCss.matchAll(/--cds-spacing-(\d+)\s*:\s*([^;]+)/g)].map(
        (match): [string, string] => [match[1]!, match[2]!.trim()],
      ),
    );
    const ours: Record<string, string> = Object.fromEntries(
      spacingCss().map((line): [string, string] => {
        const [name, value] = line.replace(";", "").split(":");
        return [name!.trim().replace("--cds-spacing-", ""), value!.trim()];
      }),
    );

    expect(ours).toEqual(declared);
  });
});

describe("carbonThemeCss", () => {
  it("declares the tokens on :root, so they inherit into every shadow root", () => {
    const css = carbonThemeCss();

    expect(css.startsWith(":root{")).toBe(true);
    expect(css).toContain("--cds-background: #ffffff;");
    // the contextual token a table header reads, which has no fallback of its own
    expect(css).toContain("--cds-layer-accent: var(--cds-layer-accent-01);");
    // and the spacing a page's own layout rules reach for
    expect(css).toContain("--cds-spacing-06: 1.5rem;");
  });
});
