import { registerIconLibrary } from "@awesome.me/webawesome/dist/components/icon/library.js";

/**
 * This package's own icons, registered under the "cofy" library name.
 *
 * Kept to exactly the icons its components use, as inline SVG resolved through a data URI -
 * so using one never makes a network request, unlike Web Awesome's own "default" library,
 * which fetches from Font Awesome's CDN.
 *
 * Importing this module is the registration: `registerIconLibrary` is safe to call more than
 * once, and ES modules only evaluate a module the first time it is imported.
 */
const ICONS: Record<string, string> = {
  gear: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="currentColor">
    <path d="M27 16.76v-1.53l1.92-1.68A2 2 0 0 0 29.3 11l-2.36-4a2 2 0 0 0-1.73-1 2 2 0 0 0-.64.1l-2.43.82a11.35 11.35 0 0 0-1.31-.75l-.51-2.52a2 2 0 0 0-2-1.61h-4.68a2 2 0 0 0-2 1.61l-.51 2.52a11.48 11.48 0 0 0-1.32.75l-2.38-.82a2 2 0 0 0-.64-.1 2 2 0 0 0-1.73 1L2.7 11a2 2 0 0 0 .38 2.52L5 15.24v1.53l-1.92 1.68A2 2 0 0 0 2.7 21l2.36 4a2 2 0 0 0 1.73 1 2 2 0 0 0 .64-.1l2.43-.82a11.35 11.35 0 0 0 1.31.75l.51 2.52a2 2 0 0 0 2 1.61h4.72a2 2 0 0 0 2-1.61l.51-2.52a11.48 11.48 0 0 0 1.32-.75l2.42.82a2 2 0 0 0 .64.1 2 2 0 0 0 1.73-1l2.28-4a2 2 0 0 0-.38-2.52ZM25.21 24l-3.43-1.16a9 9 0 0 1-2.71 1.57L18.36 28h-4.72l-.71-3.55a9.36 9.36 0 0 1-2.7-1.57L6.79 24l-2.36-4 2.72-2.4a8.9 8.9 0 0 1 0-3.13L4.43 12l2.36-4 3.43 1.16a9 9 0 0 1 2.71-1.57L13.64 4h4.72l.71 3.55a9.36 9.36 0 0 1 2.7 1.57L25.21 8l2.36 4-2.72 2.4a8.9 8.9 0 0 1 0 3.13L27.57 20Z"/>
    <path d="M16 22a6 6 0 1 1 6-6 6 6 0 0 1-6 6Zm0-10a4 4 0 1 0 4 4 4 4 0 0 0-4-4Z"/>
  </svg>`,
};

registerIconLibrary("cofy", {
  resolver: (name) => `data:image/svg+xml,${encodeURIComponent(ICONS[name] ?? "")}`,
});
