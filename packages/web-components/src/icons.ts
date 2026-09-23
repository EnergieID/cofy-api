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
  plus: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
    <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
  </svg>`,
  brand: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="1.5 0.5 6 7">
    <style>
      .arc { fill: none; stroke: currentColor; stroke-linecap: round; stroke-width: 0.6; }
      .end-arc { stroke-linecap: butt; }
    </style>
    <path class="arc end-arc" d="M 4 1 C 3.0557 1.3148 2.3148 2.0557 2 3"/>
    <path class="arc end-arc" d="M 6.4495 2 C 6.0708 1.5361 5.5681 1.1894 5 1"/>
    <path class="arc" d="M 5.8559 3 C 5.6013 2.5274 5.1759 2.1698 4.6667 2"/>
    <path class="arc end-arc" d="M 4.6667 6 C 5.0541 5.8708 5.3958 5.6319 5.65 5.3122"/>
    <path class="arc" d="M 5 7 C 5.9443 6.6852 6.6852 5.9443 7 5"/>
    <path class="arc end-arc" d="M 3.65 5.6192 C 3.852 5.7877 4.0838 5.9168 4.3333 6"/>
    <path class="arc end-arc" d="M 3 4.6667 C 3.078 4.9007 3.1965 5.1192 3.35 5.3122"/>
    <path class="arc end-arc" d="M 2 5 C 2.3148 5.9443 3.0557 6.6852 4 7"/>
    <path class="arc end-arc" d="M 4.3333 2 C 4.0838 2.0832 3.852 2.2123 3.65 2.3808"/>
    <path class="arc end-arc" d="M 3.35 2.6878 C 3.1965 2.8808 3.078 3.0993 3 3.3333"/>
    <path class="arc end-arc" d="M 2 3.6667 L 2 4.6667"/>
    <path class="arc" d="M 2 4.6667 L 2 5"/>
    <path class="arc" d="M 2 4.6667 L 3 4.6667"/>
    <path class="arc" d="M 4.6667 6 L 4.6667 7"/>
    <path class="arc" d="M 4.6667 7 L 5 7"/>
    <path class="arc end-arc" d="M 5.8559 5 L 7 5"/>
    <path class="arc end-arc" d="M 5.8559 3 L 7 3"/>
    <path class="arc" d="M 4.6667 6 L 4.3333 6"/>
    <path class="arc" d="M 4.6667 2 L 4.6667 1"/>
    <path class="arc" d="M 4.6667 1 L 5 1"/>
    <path class="arc" d="M 4.6667 2 L 4.3333 2"/>
    <path class="arc" d="M 4.6667 1 L 4 1"/>
    <path class="arc" d="M 3 4.6667 L 3 3.3333"/>
  </svg>`
};

registerIconLibrary("cofy", {
  resolver: (name) => `data:image/svg+xml,${encodeURIComponent(ICONS[name] ?? "")}`,
});
