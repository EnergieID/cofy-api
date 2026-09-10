import { spacing } from "@carbon/layout";
import { white } from "@carbon/themes";

/**
 * The contextual layer tokens, and the theme token each one resolves to.
 *
 * Carbon splits its tokens in two. Most are plain theme values (`layer-01`, `text-primary`)
 * and come straight from `@carbon/themes`. A handful are *contextual*: `--cds-layer` means
 * "the layer for wherever you are", and Carbon's stylesheet points it at a numbered token per
 * nesting level. Components read the contextual name - a table header's background is
 * `var(--cds-layer-accent)` with no fallback - so without these it renders unstyled.
 *
 * This is the outermost level, Carbon's `.cds--layer-one`. The pairs are checked against
 * Carbon's own stylesheet by a test, so an upstream change shows up there rather than as a
 * component that quietly loses its background.
 */
const LAYER_ONE: Record<string, string> = {
  layer: "layer01",
  "layer-active": "layerActive01",
  "layer-background": "layerBackground01",
  "layer-hover": "layerHover01",
  "layer-selected": "layerSelected01",
  "layer-selected-hover": "layerSelectedHover01",
  "layer-accent": "layerAccent01",
  "layer-accent-hover": "layerAccentHover01",
  "layer-accent-active": "layerAccentActive01",
  field: "field01",
  "field-hover": "fieldHover01",
  "border-subtle": "borderSubtle00",
  "border-subtle-selected": "borderSubtleSelected01",
  "border-strong": "borderStrong01",
  "border-tile": "borderTile01",
};

/**
 * Carbon's theme tokens as a stylesheet.
 *
 * Carbon's own `styles.css` declares these, but it is 1.1 MB (100 KB gzipped) of resets, grid
 * and component classes this app does not use - the values alone are a few KB. The names are
 * derived from `@carbon/themes` rather than copied, so they cannot drift from the installed
 * Carbon version.
 */
export function carbonThemeCss(theme: Record<string, unknown> = white): string {
  const values = Object.entries(theme).filter((entry): entry is [string, string] => typeof entry[1] === "string");

  const themeTokens = values.map(([name, value]) => `--cds-${tokenToCssName(name)}: ${value};`);
  const contextual = Object.entries(LAYER_ONE).map(
    ([name, source]) => `--cds-${name}: var(--cds-${tokenToCssName(source)});`,
  );

  return `:root{${themeTokens.join("")}${contextual.join("")}${spacingCss().join("")}}`;
}

/**
 * Carbon's spacing scale, as `--cds-spacing-01` upwards.
 *
 * These live in `@carbon/layout` rather than `@carbon/themes`, so they are not part of the
 * theme values above - but component and page styles reach for them, and without them every
 * such rule silently falls back to nothing.
 */
export function spacingCss(): string[] {
  return spacing.map((value, index) => `--cds-spacing-${String(index + 1).padStart(2, "0")}: ${value};`);
}

/** `layer01` -> `layer-01`, `textPrimary` -> `text-primary`. */
export function tokenToCssName(token: string): string {
  return token
    .replace(/([a-z])([A-Z])/g, "$1-$2")
    .replace(/([a-zA-Z])(\d)/g, "$1-$2")
    .toLowerCase();
}

/** The contextual token pairs, exposed so a test can check them against Carbon. */
export function layerOneTokens(): Record<string, string> {
  return { ...LAYER_ONE };
}

/** Declare the tokens on the document, where they inherit into every shadow root. */
export function applyCarbonTheme(theme?: Record<string, unknown>): void {
  const style = document.createElement("style");
  style.textContent = carbonThemeCss(theme);
  document.head.prepend(style);
}
