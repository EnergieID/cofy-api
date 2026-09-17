import { css } from "lit";
import type { CSSResultGroup } from "lit";

import { nativeStyles } from "./native-styles.js";

/**
 * Styles for a plain `<table>`, shared by the list components.
 *
 * `nativeStyles` gives `<table>`, `<th>` and `<td>` Web Awesome's real styling - borrowed rather
 * than reimplemented, so it cannot drift from what the design system actually ships. The title
 * and description above the table are `cofy-heading`, not a `<caption>`: what native.css gives
 * a caption - a single muted, smaller block - does not fit a title meant to read as a heading.
 * What is added here is behaviour Web Awesome's stylesheet has no opinion on: a clickable row.
 */
export const tableStyles: CSSResultGroup = [
  nativeStyles,
  css`
    tbody tr {
      cursor: pointer;
    }
    tbody tr:hover,
    tbody tr:focus-visible {
      background: var(--wa-color-surface-raised);
    }
    tbody tr:focus-visible {
      outline: var(--wa-focus-ring);
      outline-offset: calc(var(--wa-focus-ring-offset) * -2);
    }
    /* The empty-state row is not a row you can open. */
    tbody tr.empty,
    tbody tr.empty:hover {
      cursor: default;
      background: none;
    }
    .secondary {
      color: var(--wa-color-text-quiet);
    }
  `,
];
