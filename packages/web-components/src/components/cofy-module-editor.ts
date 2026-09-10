import { consume } from "@lit/context";
import { StateController } from "@dodona/lit-state";
import { LitElement, css, html, nothing } from "lit";
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

import "@carbon/web-components/es/components/button/button.js";
import "@carbon/web-components/es/components/heading/index.js";
import "@carbon/web-components/es/components/stack/index.js";
import "@carbon/web-components/es/components/skeleton-text/skeleton-text.js";

import { allowedModulesStoreContext, moduleStoreContext } from "../context.js";
import { toYaml } from "../yaml.js";
import "./cofy-problem-details.js";
import "./cofy-yaml-editor.js";
import type { YamlEditorChange } from "./cofy-yaml-editor.js";

/**
 * Edits one module as YAML, checked against its type's schema as you type.
 *
 * YAML because that is the form these configs are already written and reviewed in, and
 * because it covers every module type - including ones installed by a third-party package
 * that this build has never seen.
 */
@customElement("cofy-module-editor")
export class CofyModuleEditor extends LitElement {
  public static override styles = css`
    :host {
      display: block;
    }
    header {
      display: flex;
      align-items: baseline;
      gap: 0.75rem;
      margin-block-end: 1rem;
    }
    .muted {
      color: var(--cds-text-secondary, #525252);
      font-size: 0.875rem;
    }
    /* cds-stack leaves its own host as an inline box, so a block margin on it does
       nothing - it groups the buttons, and this row places them. */
    .actions {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: var(--cds-spacing-05);
      margin-block-start: var(--cds-spacing-06);
    }
    .issues {
      margin: var(--cds-spacing-05) 0 0;
      padding-left: 1rem;
      color: var(--cds-text-error, #da1e28);
      font-size: 0.875rem;
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
  `;

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

  public readonly stateController = new StateController(this);

  public override willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("slug") || changed.has("moduleId") || changed.has("moduleStore")) {
      void this.open();
    }
  }

  public override render(): TemplateResult {
    if (this.draft === null) {
      return this.moduleStore?.error != null
        ? html`<cofy-problem-details .problem=${this.moduleStore.error}></cofy-problem-details>`
        : html`<cds-skeleton-text paragraph line-count="5"></cds-skeleton-text>`;
    }

    const { draft } = this;
    const blocked = this.syntaxErrors.length > 0 || !draft.valid || draft.renamed;

    return html`
      <cds-section>
        <header>
          <cds-heading>${draft.original.display_name || draft.original.name}</cds-heading>
          <span class="muted">${draft.original.type}</span>
        </header>
      </cds-section>

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
        <cds-stack orientation="horizontal" gap="3">
          <cds-button
            ?disabled=${blocked || !draft.dirty || draft.saving}
            @click=${(): void => void this.save()}
          >
            ${draft.saving ? "Saving…" : "Save"}
          </cds-button>
          <cds-button kind="secondary" ?disabled=${!draft.dirty} @click=${(): void => this.reset()}>
            Discard
          </cds-button>
        </cds-stack>
        <span class="muted">
          ${draft.dirty ? "Unsaved changes" : this.saved ? "Saved" : "No changes"}
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
        <li>
          A module's type and name are its identity and cannot be changed here — create a new
          module instead.
        </li>
      </ul>`;
    }
    if (draft.issues.length === 0) return nothing;

    return html`<ul class="issues">
      ${draft.issues.map(
        (issue): TemplateResult => html`
          <li>
            <button type="button" @click=${(): void => this.reveal(issue.pointer)}>
              ${issue.pointer === "" ? "document" : issue.pointer}
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
