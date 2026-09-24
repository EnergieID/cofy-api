import { consume } from "@lit/context";
import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import {
  EditableValue,
  type AllowedModule,
  type AllowedModulesStore,
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
 * Creates a module, starting from a skeleton derived from the chosen type's schema.
 *
 * The type list comes from what the community is allowed to configure, so a build that has
 * never heard of a module type still offers it as soon as the server does. Picking a type is
 * itself part of the form `cofy-module-form` renders, not a separate step before it.
 */
@customElement("cofy-module-create")
export class CofyModuleCreate extends CofyElement {
  public static override styles = [
    nativeStyles,
    utilityStyles,
    css`
      :host {
        display: block;
      }
    `,
  ];

  @consume({ context: moduleStoreContext, subscribe: true })
  @state()
  public moduleStore!: ModuleStore;

  @consume({ context: allowedModulesStoreContext, subscribe: true })
  @state()
  public allowedModules!: AllowedModulesStore;

  @property({ type: String }) public slug = "";

  @state() private draft: EditableValue<ModuleSettings> | null = null;
  @state() private saving = false;
  @state() private error: ProblemError | null = null;
  @state() private mode: ModuleFormMode = "form";

  public override willUpdate(changed: Map<string, unknown>): void {
    if ((changed.has("slug") || changed.has("allowedModules")) && this.slug !== "") {
      void this.allowedModules?.ensure(this.slug);
    }
  }

  public override render(): TemplateResult {
    const catalog = this.allowedModules?.list(this.slug);
    if (catalog === undefined) {
      return html`<div class="wa-stack">
        ${Array.from({ length: 4 }, () => html`<wa-skeleton></wa-skeleton>`)}
      </div>`;
    }

    const { draft } = this;
    const blocked = draft === null || !draft.valid || this.saving;
    const hasSchema = draft !== null && catalog.some((option) => option.type === draft.current.type);

    return html`
      <div class="wa-stack">
        <cofy-heading>
          <span slot="title">${this.t("create.title")}</span>
          ${hasSchema
            ? html`<wa-button slot="actions" appearance="plain" @click=${(): void => this.toggleMode()}>
                ${this.mode === "form" ? this.t("form.viewAsYaml") : this.t("form.viewAsForm")}
              </wa-button>`
            : nothing}
        </cofy-heading>

        ${this.error === null ? nothing : html`<cofy-problem-details .problem=${this.error}></cofy-problem-details>`}

        <cofy-module-form
          .catalog=${catalog}
          .value=${draft?.current ?? null}
          .issues=${draft?.issues ?? []}
          .mode=${this.mode}
          @module-form-change=${(e: CustomEvent<{ value: ModuleSettings }>): void => this.onFormChange(e)}
        ></cofy-module-form>

        ${draft === null
          ? nothing
          : html`
              <footer class="wa-split">
                <div class="wa-cluster">
                  <wa-button variant="brand" ?disabled=${blocked} @click=${(): void => void this.create()}>
                    ${this.saving ? this.t("create.creating") : this.t("create.submit")}
                  </wa-button>
                  <wa-button appearance="plain" @click=${(): void => this.cancel()}>
                    ${this.t("create.cancel")}
                  </wa-button>
                </div>
                ${draft.issues.length === 0
                  ? nothing
                  : html`<wa-badge variant="danger">${this.t("form.issuesToggle", { count: draft.issues.length })}</wa-badge>`}
             </footer>
            `}
      </div>
    `;
  }

  private onFormChange(event: CustomEvent<{ value: ModuleSettings }>): void {
    this.error = null;
    const draft = this.draft;
    if (draft === null) {
      const created = new EditableValue(event.detail.value);
      this.draft = created;
      this.check(created);
      return;
    }
    draft.set(event.detail.value);
    this.check(draft);
  }

  private catalog(): readonly AllowedModule[] {
    return this.allowedModules?.list(this.slug) ?? [];
  }

  private check(draft: EditableValue<ModuleSettings>): void {
    const schema = this.catalog().find((option) => option.type === draft.current.type)?.schema;
    if (schema === undefined) return;
    draft.check(schema);
  }

  private async create(): Promise<void> {
    const draft = this.draft;
    if (draft === null) return;

    this.saving = true;
    this.error = null;
    try {
      const created = await this.moduleStore.create(this.slug, draft.current);
      this.dispatchEvent(
        new CustomEvent("module-created", {
          detail: { slug: this.slug, id: { type: created.type, name: created.name } },
          bubbles: true,
          composed: true,
        }),
      );
    } catch (error) {
      this.error = error as ProblemError;
    } finally {
      this.saving = false;
    }
  }

  private cancel(): void {
    this.dispatchEvent(new CustomEvent("create-cancelled", { bubbles: true, composed: true }));
  }

  private toggleMode(): void {
    this.mode = this.mode === "form" ? "yaml" : "form";
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-module-create": CofyModuleCreate;
  }
}
