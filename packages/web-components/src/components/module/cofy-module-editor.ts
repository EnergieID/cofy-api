import { consume } from "@lit/context";
import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import {
  ModuleDraft,
  type AllowedModule,
  type AllowedModulesStore,
  type ModuleId,
  type ModuleSettings,
  type ModuleStore,
  type ProblemError,
} from "@cofy/frontend-sdk";

import "@awesome.me/webawesome/dist/components/badge/badge.js";
import "@awesome.me/webawesome/dist/components/button/button.js";
import "@awesome.me/webawesome/dist/components/skeleton/skeleton.js";

import { CofyElement } from "../../cofy-element.js";
import { allowedModulesStoreContext, moduleStoreContext } from "../../context.js";
import { nativeStyles } from "../../theme/native-styles.js";
import { utilityStyles } from "../../theme/utility-styles.js";
import "../cofy-problem-details.js";
import "../layout/cofy-heading.js";
import "./cofy-module-form.js";
import type { ModuleFormMode } from "./cofy-module-form.js";

/**
 * Edits one module, checked against its type's schema as you type.
 *
 * A generated form when the type's schema is known; raw YAML otherwise - either by choice, via
 * the toggle in this component's own heading, or because the type is one this build's catalog
 * has never seen (an installed third-party module, say), in which case there is no schema to
 * generate a form from and YAML is the only option.
 */
@customElement("cofy-module-editor")
export class CofyModuleEditor extends CofyElement {
  public static override styles = [
    nativeStyles,
    utilityStyles,
    css`
      :host {
        display: block;
      }
      .issues {
        margin: var(--wa-space-m) 0 0;
        padding-inline-start: var(--wa-space-m);
        color: var(--wa-color-danger-border-loud);
        font-size: var(--wa-font-size-s);
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
  @state() private saveError: ProblemError | null = null;
  @state() private saved = false;
  @state() private mode: ModuleFormMode = "form";

  public override willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("slug") || changed.has("moduleId") || changed.has("moduleStore")) {
      void this.open();
    }
  }

  public override render(): TemplateResult {
    if (this.draft === null) {
      return this.moduleStore?.error != null
        ? html`<cofy-problem-details .problem=${this.moduleStore.error}></cofy-problem-details>`
        : html`<div class="wa-stack">
            ${Array.from({ length: 5 }, () => html`<wa-skeleton></wa-skeleton>`)}
          </div>`;
    }

    const { draft } = this;
    const blocked = !draft.valid || draft.renamed;
    const hasSchema = this.catalog().some((option) => option.type === draft.original.type);

    return html`
      <div class="wa-stack">
        <cofy-heading>
          <span slot="title">${this.t("editor.title")}</span>
          ${hasSchema
            ? html`<wa-button slot="actions" appearance="plain" @click=${(): void => this.toggleMode()}>
                ${this.mode === "form" ? this.t("form.viewAsYaml") : this.t("form.viewAsForm")}
              </wa-button>`
            : nothing}
        </cofy-heading>

        ${this.saveError === null
          ? nothing
          : html`<cofy-problem-details .problem=${this.saveError}></cofy-problem-details>`}

        <cofy-module-form
          .catalog=${this.catalog()}
          .value=${draft.current}
          .issues=${draft.issues}
          .mode=${this.mode}
          locked
          @module-form-change=${(e: CustomEvent<{ value: ModuleSettings }>): void => this.onFormChange(e)}
        ></cofy-module-form>

        ${draft.renamed
          ? html`<ul class="issues">
              <li>${this.t("editor.renamed")}</li>
            </ul>`
          : nothing}

        <footer class="wa-split">
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
          <div class="wa-cluster">
            <span class="wa-caption-s">
              ${draft.dirty ? this.t("editor.unsaved") : this.saved ? this.t("editor.saved") : this.t("editor.unchanged")}
            </span>
          ${draft.issues.length === 0
              ? nothing
              : html`<wa-badge variant="danger">${this.t("form.issuesToggle", { count: draft.issues.length })}</wa-badge>`}
          </div>
        </footer>
      </div>
    `;
  }

  private async open(): Promise<void> {
    const { slug, moduleId, moduleStore } = this;
    if (slug === "" || moduleId === null || moduleStore === undefined) return;

    this.saveError = null;
    this.saved = false;
    this.mode = "form";
    await Promise.all([moduleStore.ensure(slug), this.allowedModules?.ensure(slug)]);

    const stored = moduleStore.find(slug, moduleId);
    if (stored === undefined) {
      this.draft = null;
      return;
    }

    const draft = new ModuleDraft(stored);
    this.draft = draft;
    this.check(draft);
  }

  private onFormChange(event: CustomEvent<{ value: ModuleSettings }>): void {
    const draft = this.draft;
    if (draft === null) return;

    draft.set(event.detail.value);
    this.check(draft);
    this.saved = false;
  }

  private catalog(): readonly AllowedModule[] {
    return this.allowedModules?.list(this.slug) ?? [];
  }

  private check(draft: ModuleDraft): void {
    const schema = this.catalog().find((option) => option.type === draft.original.type)?.schema;
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
    this.check(draft);
  }

  private toggleMode(): void {
    this.mode = this.mode === "form" ? "yaml" : "form";
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-module-editor": CofyModuleEditor;
  }
}
