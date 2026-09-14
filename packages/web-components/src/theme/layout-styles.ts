import { unsafeCSS } from "lit";
import type { CSSResult } from "lit";
import layout from "@awesome.me/webawesome/dist/styles/utilities/layout.css?raw";

/**
 * Web Awesome's `wa-cluster` / `wa-split` / `wa-stack` / ... layout utility classes.
 *
 * Like `nativeStyles`, this is a document stylesheet that does not cross a shadow boundary, so
 * a `class="wa-cluster"` div inside one of our components was silently unstyled - `display`
 * stayed `block` and there was no gap between its children, no matter how wide the class list
 * looked in the markup. Imported straight from the installed package, so it cannot drift.
 *
 * `utilities/layout.css` specifically, rather than `utilities.css`: the latter is only an
 * index of `@import`s for every utility this package does not use (icon sizing, visibility,
 * scroll locking, ...), and pulling in the whole index would mean resolving each of those too,
 * for nothing this package renders. `layout.css` is self-contained - no `@import`s of its own.
 */
export const layoutStyles: CSSResult = unsafeCSS(layout);
