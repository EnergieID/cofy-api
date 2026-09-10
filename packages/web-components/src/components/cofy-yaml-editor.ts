import { linter, lintGutter, type Diagnostic } from "@codemirror/lint";
import { EditorState, type Extension } from "@codemirror/state";
import { EditorView, keymap } from "@codemirror/view";
import { yaml as yamlLanguage } from "@codemirror/lang-yaml";
import { basicSetup } from "codemirror";
import { LitElement, css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property } from "lit/decorators.js";
import { parseDocument } from "yaml";

/** What the editor's current text means, recomputed on every change. */
export interface YamlEditorChange {
  text: string;
  /** The parsed document, or `undefined` when the text is not valid YAML. */
  value: unknown;
  /** Problems in the text itself, before anything schema-aware looks at it. */
  syntaxErrors: string[];
}

/** One schema problem to show against a value inside the document. */
export interface YamlEditorIssue {
  /** JSON Pointer into the parsed value, e.g. `/source/api_key`. */
  pointer: string;
  message: string;
}

/**
 * A YAML editor that reports what it parses and marks up problems in place.
 *
 * It knows nothing about modules or schemas: the host parses, validates, and hands back
 * {@link issues}, which are mapped onto ranges by resolving each pointer against the
 * document's own node positions.
 */
@customElement("cofy-yaml-editor")
export class CofyYamlEditor extends LitElement {
  public static override styles = css`
    :host {
      display: block;
    }
    .editor {
      border: 1px solid var(--cds-border-strong, #8d8d8d);
      background: var(--cds-field, #f4f4f4);
    }
    .cm-editor {
      max-block-size: 60vh;
    }
    .cm-editor.cm-focused {
      outline: 2px solid var(--cds-focus, #0f62fe);
      outline-offset: -2px;
    }
  `;

  /** The document to edit. Assigning replaces the editor's contents. */
  @property({ type: String }) public text = "";

  /** Schema problems to mark up, supplied by the host after it validates. */
  @property({ attribute: false }) public issues: YamlEditorIssue[] = [];

  private view: EditorView | null = null;

  public override render(): TemplateResult {
    return html`<div class="editor"></div>`;
  }

  public override firstUpdated(): void {
    const parent = this.renderRoot.querySelector(".editor");
    if (parent === null) return;

    this.view = new EditorView({
      parent,
      state: EditorState.create({ doc: this.text, extensions: this.extensions() }),
    });
  }

  public override updated(changed: Map<string, unknown>): void {
    if (this.view === null) return;

    if (changed.has("text") && this.text !== this.view.state.doc.toString()) {
      this.view.dispatch({
        changes: { from: 0, to: this.view.state.doc.length, insert: this.text },
      });
    }
    if (changed.has("issues")) {
      // Re-run the linter so newly supplied issues are drawn.
      this.view.dispatch({});
    }
  }

  public override disconnectedCallback(): void {
    super.disconnectedCallback();
    this.view?.destroy();
    this.view = null;
  }

  /** Move the cursor to the value a pointer addresses, and focus the editor. */
  public revealPointer(pointer: string): void {
    const view = this.view;
    if (view === null) return;

    const range = locate(view.state.doc.toString(), pointer);
    if (range === null) return;

    view.dispatch({ selection: { anchor: range[0] }, scrollIntoView: true });
    view.focus();
  }

  private extensions(): Extension[] {
    return [
      basicSetup,
      yamlLanguage(),
      lintGutter(),
      linter((view) => this.diagnostics(view)),
      keymap.of([]),
      EditorView.updateListener.of((update) => {
        if (!update.docChanged) return;
        this.emit(update.state.doc.toString());
      }),
    ];
  }

  private diagnostics(view: EditorView): Diagnostic[] {
    const text = view.state.doc.toString();
    const document = parseDocument(text);

    const syntax: Diagnostic[] = document.errors.map((error) => ({
      from: error.pos[0],
      to: Math.max(error.pos[1], error.pos[0] + 1),
      severity: "error",
      message: error.message,
    }));
    if (syntax.length > 0) return syntax;

    return this.issues.map((issue) => {
      const range = locate(text, issue.pointer) ?? [0, Math.min(1, text.length)];
      return { from: range[0], to: range[1], severity: "error", message: issue.message };
    });
  }

  private emit(text: string): void {
    const document = parseDocument(text);
    const detail: YamlEditorChange = {
      text,
      value: document.errors.length > 0 ? undefined : document.toJS(),
      syntaxErrors: document.errors.map((error) => error.message),
    };
    this.text = text;
    this.dispatchEvent(new CustomEvent<YamlEditorChange>("yaml-change", { detail }));
  }
}

/**
 * Find the source range of the value a JSON Pointer addresses.
 *
 * Uses the YAML document's own node ranges rather than searching the text, so a key that
 * appears in several places is still resolved through its actual path.
 */
export function locate(text: string, pointer: string): [number, number] | null {
  if (pointer === "") return null;

  const document = parseDocument(text);
  if (document.errors.length > 0) return null;

  const path = pointer
    .slice(1)
    .split("/")
    .map((part) => part.replace(/~1/g, "/").replace(/~0/g, "~"));

  const node = document.getIn(
    path.map((part) => (/^\d+$/.test(part) ? Number(part) : part)),
    true,
  ) as { range?: [number, number, number] } | undefined;

  if (node?.range === undefined) return null;
  return [node.range[0], node.range[1]];
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-yaml-editor": CofyYamlEditor;
  }
}
