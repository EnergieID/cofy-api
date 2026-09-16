import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { EditorView } from "@codemirror/view";
import type { Extension } from "@codemirror/state";
import { tags } from "@lezer/highlight";

/**
 * Colours the editor from theme tokens.
 *
 * Every value is a `var()`, and custom properties inherit through shadow roots, so the editor
 * follows a colour-scheme change on its own - no listener, no rebuild. That is the reason not
 * to ship a ready-made CodeMirror theme like One Dark: one would need swapping on every change
 * and would sit outside the page's palette while doing it.
 *
 * The `--cofy-syntax-*` defaults below are the light ones. Dark needs *different* tints rather
 * than the same colour on a darker ground, and a `var()` fallback cannot express that, so
 * `theme/syntax.css` supplies both schemes and this file degrades to light without it.
 */
const highlight = HighlightStyle.define([
  // Keys are the bulk of a YAML document and the thing you scan for.
  { tag: tags.propertyName, color: "var(--cofy-syntax-key, var(--wa-color-indigo-40))" },
  { tag: [tags.string, tags.special(tags.string)], color: "var(--cofy-syntax-string, var(--wa-color-green-30))" },
  { tag: tags.number, color: "var(--cofy-syntax-number, var(--wa-color-cyan-30))" },
  { tag: [tags.bool, tags.null, tags.atom], color: "var(--cofy-syntax-atom, var(--wa-color-purple-40))" },
  {
    tag: [tags.comment, tags.lineComment],
    color: "var(--cofy-syntax-comment, var(--wa-color-gray-50))",
    fontStyle: "italic",
  },
  // Document markers, directives, anchors and tags - the YAML-about-YAML parts.
  { tag: tags.meta, color: "var(--cofy-syntax-meta, var(--wa-color-orange-40))" },
  {
    tag: [tags.punctuation, tags.separator],
    color: "var(--cofy-syntax-punctuation, var(--wa-color-gray-50))",
  },
  { tag: tags.invalid, color: "var(--cofy-syntax-invalid, var(--wa-color-red-40))" },
]);

/** The editor's own chrome - everything that is not a token in the document. */
const chrome = EditorView.theme({
  "&": {
    color: "var(--wa-color-text-normal)",
    backgroundColor: "var(--wa-form-control-background-color)",
  },
  ".cm-content": {
    caretColor: "var(--wa-color-text-normal)",
    fontFamily: "var(--wa-font-family-code, monospace)",
    // Same inset as every other control's own value from its border - `wa-textarea`'s own.
    padding: "var(--wa-form-control-padding-block) var(--wa-form-control-padding-inline)",
  },
  ".cm-cursor, .cm-dropCursor": { borderLeftColor: "var(--wa-color-text-normal)" },
  "&.cm-focused .cm-selectionBackground, .cm-selectionBackground, ::selection": {
    backgroundColor: "var(--wa-color-brand-fill-quiet) !important",
  },
  // "-surface-raised" happens to equal the editor's own background in light theme (both plain
  // white), so the active line disappeared there; "-surface-lowered" differs from it in both.
  ".cm-activeLine": { backgroundColor: "var(--wa-color-surface-lowered)" },
  ".cm-gutters": {
    backgroundColor: "var(--wa-form-control-background-color)",
    color: "var(--wa-color-text-quiet)",
    border: "none",
    borderInlineEnd: "var(--wa-border-width-s) solid var(--wa-color-surface-border)",
    paddingInlineStart: "var(--wa-form-control-padding-inline)",
  },
  ".cm-activeLineGutter": {
    backgroundColor: "var(--wa-color-surface-lowered)",
    color: "var(--wa-color-text-normal)",
  },
  ".cm-foldPlaceholder": {
    backgroundColor: "var(--wa-color-neutral-fill-quiet)",
    color: "var(--wa-color-text-quiet)",
    border: "none",
  },
  ".cm-tooltip": {
    backgroundColor: "var(--wa-color-surface-raised)",
    color: "var(--wa-color-text-normal)",
    border: "var(--wa-border-width-s) solid var(--wa-color-surface-border)",
  },
  ".cm-diagnostic-error": { borderInlineStartColor: "var(--wa-color-danger-border-loud)" },
  ".cm-lintRange-error": {
    backgroundImage: "none",
    textDecoration: "underline wavy var(--wa-color-danger-border-loud)",
  },
  ".cm-panels": {
    backgroundColor: "var(--wa-color-surface-raised)",
    color: "var(--wa-color-text-normal)",
  },
});

/** The page's colours for the editor, document and chrome alike. */
export function cofyEditorTheme(): Extension {
  return [chrome, syntaxHighlighting(highlight)];
}
