import { consume } from "@lit/context";
import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import {
  ModuleDraft,
  type AllowedModulesStore,
  type ModuleId,
  type ModuleSettings,
  type ModuleStore,
  type ProblemError,
} from "@cofy/frontend-sdk";

import "@awesome.me/webawesome/dist/components/button/button.js";
import "@awesome.me/webawesome/dist/components/skeleton/skeleton.js";

import { CofyElement } from "../../cofy-element.js";
import { allowedModulesStoreContext, moduleStoreContext } from "../../context.js";
import { layoutStyles } from "../../theme/layout-styles.js";
import { nativeStyles } from "../../theme/native-styles.js";
import { toYaml } from "../../yaml.js";
import "../cofy-problem-details.js";
import "../editor/cofy-yaml-editor.js";
import type { YamlEditorChange } from "../editor/cofy-yaml-editor.js";

/**
 * Edits one module as YAML, checked against its type's schema as you type.
 *
 * YAML because that is the form these configs are already written and reviewed in, and
 * because it covers every module type - including ones installed by a third-party package
 * that this build has never seen.
 */
@customElement("cofy-module-editor")
export class CofyModuleEditor extends CofyElement {
  public static override styles = [
    nativeStyles,
    layoutStyles,
    css`
      :host {
        display: block;
      }
      header {
        display: flex;
        align-items: baseline;
        gap: 0.75rem;
        margin-block-end: 1rem;
      }
      /* native.css spaces a heading below itself whenever something follows it in the flow,
         which here is the inline type badge beside it, not below - reset for the flex row. */
      h2 {
        margin: 0;
      }
      .muted {
        color: var(--wa-color-text-quiet, #525252);
        font-size: 0.875rem;
      }
      .actions {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--wa-space-m);
        margin-block-start: var(--wa-space-l);
      }
      .issues {
        margin: var(--wa-space-m) 0 0;
        padding-inline-start: 1rem;
        color: var(--wa-color-danger-border-loud, #da1e28);
        font-size: 0.875rem;
      }
      .skeleton {
        display: flex;
        flex-direction: column;
        gap: var(--wa-space-xs);
      }
      .issues button {
        background: none;
        border: 0;
        padding: 0;
        color: inherit;
        text-decoration: underline;
        cursor: pointer;
        font: inherit;
      }
    `,
  ];

  @consume({ context: moduleStoreContext, subscribe: true })
  public moduleStore!: ModuleStore;

  @consume({ context: allowedModulesStoreContext, subscribe: true })
  public allowedModules!: AllowedModulesStore;

  @property({ type: String }) public slug = "";
  @property({ attribute: false }) public moduleId: ModuleId | null = null;

  @state() private draft: ModuleDraft | null = null;
  @state() private text = "";
  @state() private syntaxErrors: string[] = [];
  @state() private saveError: ProblemError | null = null;
  @state() private saved = false;

  public override willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("slug") || changed.has("moduleId") || changed.has("moduleStore")) {
      void this.open();
    }
  }

  public override render(): TemplateResult {
    if (this.draft === null) {
      return this.moduleStore?.error != null
        ? html`<cofy-problem-details .problem=${this.moduleStore.error}></cofy-problem-details>`
        : html`<div class="skeleton">
            ${Array.from({ length: 5 }, () => html`<wa-skeleton></wa-skeleton>`)}
          </div>`;
    }

    const { draft } = this;
    const blocked = this.syntaxErrors.length > 0 || !draft.valid || draft.renamed;

    return html`
      <header>
        <h2>${draft.original.display_name || draft.original.name}</h2>
        <span class="muted">${draft.original.type}</span>
      </header>

      ${this.saveError === null
        ? nothing
        : html`<cofy-problem-details .problem=${this.saveError}></cofy-problem-details>`}

      <cofy-yaml-editor
        .text=${this.text}
        .issues=${draft.issues.map((issue) => ({ pointer: issue.pointer, message: issue.message }))}
        @yaml-change=${(e: CustomEvent<YamlEditorChange>): void => this.onChange(e)}
      ></cofy-yaml-editor>

      ${this.problems(draft)}

      <footer class="actions">
        <div class="wa-cluster">
          <wa-button
            variant="brand"
            ?disabled=${blocked || !draft.dirty || draft.saving}
            @click=${(): void => void this.save()}
          >
            ${draft.saving ? this.t("editor.saving") : this.t("editor.save")}
          </wa-button>
          <wa-button appearance="outlined" ?disabled=${!draft.dirty} @click=${(): void => this.reset()}>
            ${this.t("editor.discard")}
          </wa-button>
        </div>
        <span class="muted">
          ${draft.dirty ? this.t("editor.unsaved") : this.saved ? this.t("editor.saved") : this.t("editor.unchanged")}
        </span>
      </footer>
    `;
  }

  private problems(draft: ModuleDraft): TemplateResult | typeof nothing {
    if (this.syntaxErrors.length > 0) {
      return html`<ul class="issues">
        ${this.syntaxErrors.map((message) => html`<li>${message}</li>`)}
      </ul>`;
    }
    if (draft.renamed) {
      return html`<ul class="issues">
        <li>${this.t("editor.renamed")}</li>
      </ul>`;
    }
    if (draft.issues.length === 0) return nothing;

    return html`<ul class="issues">
      ${draft.issues.map(
        (issue): TemplateResult => html`
          <li>
            <button type="button" @click=${(): void => this.reveal(issue.pointer)}>
              ${issue.pointer === "" ? this.t("editor.documentRoot") : issue.pointer}
            </button>
            — ${issue.message}
          </li>
        `,
      )}
    </ul>`;
  }

  private async open(): Promise<void> {
    const { slug, moduleId, moduleStore } = this;
    if (slug === "" || moduleId === null || moduleStore === undefined) return;

    this.saveError = null;
    this.saved = false;
    await Promise.all([moduleStore.ensure(slug), this.allowedModules?.ensure(slug)]);

    const stored = moduleStore.find(slug, moduleId);
    if (stored === undefined) {
      this.draft = null;
      return;
    }

    const draft = new ModuleDraft(stored);
    this.draft = draft;
    this.text = toYaml(stored);
    this.syntaxErrors = [];
    this.check(draft);
  }

  private onChange(event: CustomEvent<YamlEditorChange>): void {
    const { text, value, syntaxErrors } = event.detail;
    // Track what the editor holds. Without this the property still says what was first
    // loaded, so discarding - which sets it back to exactly that - looks like no change at
    // all and the editor keeps the edits.
    this.text = text;
    this.syntaxErrors = syntaxErrors;
    this.saved = false;

    const draft = this.draft;
    if (draft === null || syntaxErrors.length > 0) return;

    draft.set(value as ModuleSettings);
    this.check(draft);
    this.requestUpdate();
  }

  private check(draft: ModuleDraft): void {
    const schema = this.allowedModules?.find(this.slug, draft.original.type)?.schema;
    if (schema === undefined) return;
    draft.check(schema);
  }

  private async save(): Promise<void> {
    const draft = this.draft;
    if (draft === null) return;

    this.saveError = null;
    try {
      const saved = await draft.save(this.moduleStore, this.slug);
      // Reopen against what the server actually stored, so a second edit starts from there
      // and any value the server normalised is visible.
      this.draft = new ModuleDraft(saved);
      this.text = toYaml(saved);
      this.saved = true;
      this.check(this.draft);
    } catch (error) {
      this.saveError = error as ProblemError;
    }
  }

  private reset(): void {
    const draft = this.draft;
    if (draft === null) return;
    draft.reset();
    this.text = toYaml(draft.original);
    this.syntaxErrors = [];
    this.check(draft);
  }

  private reveal(pointer: string): void {
    this.renderRoot.querySelector("cofy-yaml-editor")?.revealPointer(pointer);
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-module-editor": CofyModuleEditor;
  }
}
