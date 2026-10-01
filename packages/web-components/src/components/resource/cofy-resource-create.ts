import { consume, provide } from "@lit/context";
import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import {
  EditableValue,
  type AllowedResource,
  type AllowedResourcesStore,
  type ProblemError,
  type ResourceSettings,
  type ResourceStore,
} from "@cofy/frontend-sdk";

import "@awesome.me/webawesome/dist/components/badge/badge.js";
import "@awesome.me/webawesome/dist/components/button/button.js";
import "@awesome.me/webawesome/dist/components/skeleton/skeleton.js";

import { CofyElement } from "../../cofy-element.js";
import { allowedResourcesStoreContext, communitySlugContext, resourceStoreContext } from "../../context.js";
import { nativeStyles } from "../../theme/native-styles.js";
import { utilityStyles } from "../../theme/utility-styles.js";
import "../cofy-problem-details.js";
import "../layout/cofy-heading.js";
import "../module/cofy-module-form.js";
import type { ModuleFormMode } from "../module/cofy-module-form.js";

/** Creates a resource, starting from a skeleton derived from the chosen kind's schema, like `cofy-module-create`. */
@customElement("cofy-resource-create")
export class CofyResourceCreate extends CofyElement {
  public static override styles = [
    nativeStyles,
    utilityStyles,
    css`
      :host {
        display: block;
      }
    `,
  ];

  @consume({ context: resourceStoreContext, subscribe: true })
  @state()
  public resourceStore!: ResourceStore;

  @consume({ context: allowedResourcesStoreContext, subscribe: true })
  @state()
  public allowedResources!: AllowedResourcesStore;

  // Provided, so the reference fields in the form list this community's resources.
  @provide({ context: communitySlugContext })
  @property({ type: String })
  public slug = "";

  @state() private draft: EditableValue<ResourceSettings> | null = null;
  @state() private saving = false;
  @state() private error: ProblemError | null = null;
  @state() private mode: ModuleFormMode = "form";

  public override willUpdate(changed: Map<string, unknown>): void {
    if ((changed.has("slug") || changed.has("allowedResources")) && this.slug !== "") {
      void this.allowedResources?.ensure(this.slug);
    }
  }

  public override render(): TemplateResult {
    const catalog = this.allowedResources?.list(this.slug);
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
          <span slot="title">${this.t("resourceCreate.title")}</span>
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
          typeLabel=${this.t("form.resourceKind")}
          @module-form-change=${(e: CustomEvent<{ value: ResourceSettings }>): void => this.onFormChange(e)}
        ></cofy-module-form>

        ${draft === null
          ? nothing
          : html`
              <footer class="wa-split">
                <div class="wa-cluster">
                  <wa-button variant="brand" ?disabled=${blocked} @click=${(): void => void this.create()}>
                    ${this.saving ? this.t("resourceCreate.creating") : this.t("resourceCreate.submit")}
                  </wa-button>
                  <wa-button appearance="plain" @click=${(): void => this.cancel()}>
                    ${this.t("resourceCreate.cancel")}
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

  private onFormChange(event: CustomEvent<{ value: ResourceSettings }>): void {
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

  private catalog(): readonly AllowedResource[] {
    return this.allowedResources?.list(this.slug) ?? [];
  }

  private check(draft: EditableValue<ResourceSettings>): void {
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
      const created = await this.resourceStore.create(this.slug, draft.current);
      this.dispatchEvent(
        new CustomEvent("resource-created", {
          detail: { slug: this.slug, name: created.name },
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
    "cofy-resource-create": CofyResourceCreate;
  }
}
