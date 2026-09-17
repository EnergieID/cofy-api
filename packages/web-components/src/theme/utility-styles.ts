import { unsafeCSS } from "lit";
import type { CSSResult } from "lit";
import utilities from "@awesome.me/webawesome/dist/styles/utilities.css?inline";

/**
 * Every Web Awesome CSS utility class (`wa-stack`, `wa-cluster`, `wa-gap-*`, `wa-caption-*`,
 * `wa-color-text-*`, `wa-form-control-label`, `wa-border-radius-*`, `wa-visually-hidden`, ...) -
 * the full set `utilities.css` documents as Web Awesome's own single entry point for them,
 * included in each field/component's own `static styles` the same way `nativeStyles` is.
 *
 * `utilities.css` itself is nothing but `@import`s of the individual files that actually define
 * these classes (plus `layers.css`, which fixes the relative priority between the `wa-native`
 * and `wa-utilities` cascade layers so a utility class can override a native element's own
 * styling), not usable as-is inside a shadow root: an `@import url(...)` left in an adopted
 * stylesheet resolves against the *document's* URL, not this package's, so it 404s for every
 * consumer. The `?inline` suffix (unlike `?raw`) asks Vite to run the file through its real CSS
 * pipeline first - resolving every `@import` against this file's own location and inlining the
 * result - and hand back that resolved text as a string, so there is no `@import` left to fail
 * and nothing here to hand-parse or strip; `layers.css`'s own ordering comes along with it.
 */
export const utilityStyles: CSSResult = unsafeCSS(utilities);
