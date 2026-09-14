import { unsafeCSS } from "lit";
import type { CSSResult } from "lit";
import native from "@awesome.me/webawesome/dist/styles/native.css?raw";

/**
 * Web Awesome's styling for plain HTML elements - headings, tables, lists, and the rest.
 *
 * `native.css` is a document stylesheet, and every component in this package renders into a
 * shadow root, which document stylesheets do not cross - a `<table>` or an `<h2>` inside one
 * arrives unstyled. Adopting the real file into each shadow root - rather than
 * hand-reimplementing the rules we happen to need - is what this is, imported straight from
 * the installed `@awesome.me/webawesome` so it cannot drift from it the way a hand-copied rule
 * silently did before. The `?raw` import is resolved at build time (Vite's own, whether this
 * package's own build or a consuming app's): the string is inlined into the compiled output,
 * so nothing at runtime, in any consumer, needs to know this ever came from a `?raw` import.
 *
 * Two things native.css cannot supply itself, added here:
 *
 * - `@import`s. The three at its top pull in `@layer` ordering and the custom properties an
 *   icon's sizing utility classes use - neither relevant to styling plain elements - and an
 *   `@import url(...)` inside an adopted stylesheet resolves against the *document's* URL, not
 *   this package's, so left in place it would 404 for every consumer regardless. `?raw` gives
 *   back the literal file text, imports included, so they are stripped below.
 * - A `box-sizing` anchor. native.css anchors its `box-sizing: border-box` reset on the real
 *   `html` element and has every other element `inherit` it - so inside a shadow root, which
 *   has no `html` of its own, that inheritance chain finds nothing of ours to anchor to. Left
 *   alone, a shadow-rooted element born with the browser's true initial value - `content-box`
 *   - silently becomes the chain's anchor instead, and that wrong value flows into anything
 *   nested below it, including a further component's own shadow root: Web Awesome's own
 *   components use the same `inherit`-based pattern internally, so a plain `<wa-button>` here
 *   once rendered with its padding added on top of its width rather than inside it, visibly
 *   overlapping its neighbour. `:host` supplies the anchor a shadow root does not otherwise
 *   have.
 */
export const nativeStyles: CSSResult = unsafeCSS(
  `:host {\n  box-sizing: border-box;\n}\n\n${native.replace(/^@import\s+url\([^)]*\);\s*\n/gm, "")}`,
);
