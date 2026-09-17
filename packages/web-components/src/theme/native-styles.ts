import { unsafeCSS } from "lit";
import type { CSSResult } from "lit";
import native from "@awesome.me/webawesome/dist/styles/native.css?inline";

/**
 * Web Awesome's styling for plain HTML elements - headings, tables, lists, and the rest.
 *
 * `native.css` is a document stylesheet, and every component in this package renders into a
 * shadow root, which document stylesheets do not cross - a `<table>` or an `<h2>` inside one
 * arrives unstyled. Adopting the real file into each shadow root - rather than
 * hand-reimplementing the rules we happen to need - is what this is, imported straight from
 * the installed `@awesome.me/webawesome` so it cannot drift from it the way a hand-copied rule
 * silently did before. `native.css` itself pulls in a few more files by `@import` (`@layer`
 * ordering, icon-sizing custom properties, native-element colour variants) - an
 * `@import url(...)` left inside an adopted stylesheet resolves against the *document's* URL,
 * not this package's, so it 404s for every consumer. `?inline` (unlike `?raw`) runs the file
 * through Vite's real CSS pipeline first, resolving every `@import` against this file's own
 * location, and hands back that already-resolved text as a string - nothing left to fail, and
 * nothing here to hand-strip.
 *
 * One thing native.css still cannot supply itself, added here: a `box-sizing` anchor.
 * native.css anchors its `box-sizing: border-box` reset on the real `html` element and has
 * every other element `inherit` it - so inside a shadow root, which has no `html` of its own,
 * that inheritance chain finds nothing of ours to anchor to. Left alone, a shadow-rooted
 * element born with the browser's true initial value - `content-box` - silently becomes the
 * chain's anchor instead, and that wrong value flows into anything nested below it, including a
 * further component's own shadow root: Web Awesome's own components use the same
 * `inherit`-based pattern internally, so a plain `<wa-button>` here once rendered with its
 * padding added on top of its width rather than inside it, visibly overlapping its neighbour.
 * `:host` supplies the anchor a shadow root does not otherwise have.
 */
export const nativeStyles: CSSResult = unsafeCSS(`:host {\n  box-sizing: border-box;\n}\n\n${native}`);
