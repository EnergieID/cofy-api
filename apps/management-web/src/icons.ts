import { registerIconLibrary } from "@awesome.me/webawesome/dist/components/icon/library.js";

/** A transparent 1×1 SVG, as a data URI so resolving it touches no network. */
const BLANK = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1 1'%3E%3C/svg%3E";

/**
 * Stop Web Awesome fetching icons from Font Awesome's CDN.
 *
 * Its default icon library resolves a name to a URL on `ka-f.fontawesome.com` and fetches it at
 * runtime, and the published package ships no SVGs to self-host instead. A console that an
 * operator may run on an isolated network cannot depend on that.
 *
 * `@cofy/web-components` registers its own icons under the "cofy" library, so nothing this
 * console renders should ever ask for the default one. But a component can ask on its own
 * behalf: `wa-page` renders a hamburger for its mobile navigation, and slot fallback content is
 * still constructed and connected even when a slot is filled, so overriding the slot does not
 * stop it. Replacing the resolver does, for every component, now and later.
 *
 * If real Font Awesome icons are ever wanted, this is where they arrive: download the SVGs,
 * serve them, and resolve names against that directory instead.
 */
export function useLocalIcons(): void {
  registerIconLibrary("default", { resolver: () => BLANK });
}
