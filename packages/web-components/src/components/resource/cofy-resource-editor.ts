import { provide } from "@lit/context";
import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import {
  ResourceDraft,
  type AllowedResource,
  type ProblemError,
  type ResourceSettings,
} from "@cofy/frontend-sdk";

import "@awesome.me/webawesome/dist/components/badge/badge.js";
import "@awesome.me/webawesome/dist/components/button/button.js";
import "@awesome.me/webawesome/dist/components/skeleton/skeleton.js";

import { CofyElement } from "../../cofy-element.js";
import { communitySlugContext } from "../../context.js";
import { nativeStyles } from "../../theme/native-styles.js";
import { utilityStyles } from "../../theme/utility-styles.js";
import "../cofy-problem-details.js";
import "../layout/cofy-heading.js";
import "../module/cofy-module-form.js";
import type { ModuleFormMode } from "../module/cofy-module-form.js";

/** Edits one resource, checked against its kind's schema as you type, like `cofy-module-editor`. */
@customElement("cofy-resource-editor")
export class CofyResourceEditor extends CofyElement {
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

  // Provided, so the reference fields in the form list this community's resources.
  @provide({ context: communitySlugContext })
  @property({ type: String })
  public slug = "";

  @property({ type: String }) public name = "";

  @state() private draft: ResourceDraft | null = null;
  @state() private saveError: ProblemError | null = null;
  @state() private saved = false;
  @state() private mode: ModuleFormMode = "form";

  public override willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("slug") || changed.has("name") || changed.has("cofy")) this.close();
    // Rendering without a draft reads what it waits for, so its arrival comes back here.
    if (this.draft === null) this.open();
  }

  public override render(): TemplateResult {
    if (this.draft === null) {
      const error = this.cofy?.resources.error(this.slug) ?? this.cofy?.allowedResources.error(this.slug) ?? null;
      return error !== null
        ? html`<cofy-problem-details .problem=${error}></cofy-problem-details>`
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
          <span slot="title">${this.t("resourceEditor.title")}</span>
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
          typeLabel=${this.t("form.resourceKind")}
          locked
          @module-form-change=${(e: CustomEvent<{ value: ResourceSettings }>): void => this.onFormChange(e)}
        ></cofy-module-form>

        ${draft.renamed
          ? html`<ul class="issues">
              <li>${this.t("resourceEditor.renamed")}</li>
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

  /** Start editing the stored resource, once it and its community's catalog are loaded. */
  private open(): void {
    const { slug, name, cofy } = this;
    if (slug === "" || name === "" || cofy === undefined) return;

    const stored = cofy.resources.get(slug, name);
    if (stored === undefined || cofy.allowedResources.all(slug) === undefined) return;

    const draft = new ResourceDraft(stored);
    this.draft = draft;
    this.check(draft);
  }

  private close(): void {
    this.draft = null;
    this.saveError = null;
    this.saved = false;
    this.mode = "form";
  }

  private onFormChange(event: CustomEvent<{ value: ResourceSettings }>): void {
    const draft = this.draft;
    if (draft === null) return;

    draft.set(event.detail.value);
    this.check(draft);
    this.saved = false;
  }

  private catalog(): readonly AllowedResource[] {
    return this.cofy?.allowedResources.all(this.slug) ?? [];
  }

  private check(draft: ResourceDraft): void {
    const schema = this.catalog().find((option) => option.type === draft.original.type)?.schema;
    if (schema === undefined) return;
    draft.check(schema);
  }

  private async save(): Promise<void> {
    const { draft, cofy } = this;
    if (draft === null || cofy === undefined) return;

    this.saveError = null;
    try {
      const saved = await draft.save(cofy.resources, this.slug);
      // Reopen against what the server actually stored, as `cofy-module-editor` does.
      this.draft = new ResourceDraft(saved);
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
    "cofy-resource-editor": CofyResourceEditor;
  }
}
