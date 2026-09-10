import { consume } from "@lit/context";
import { StateController } from "@dodona/lit-state";
import { LitElement, css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { moduleKey, type ModuleSettings, type ModuleStore, type ProblemError } from "@cofy/frontend-sdk";

import "@carbon/web-components/es/components/button/button.js";
import "@carbon/web-components/es/components/data-table/index.js";
import "@carbon/web-components/es/components/tag/tag.js";

import { moduleStoreContext } from "../context.js";
import "./cofy-problem-details.js";

/**
 * The modules configured in a community.
 *
 * Follows Carbon's data-table pattern: the title and toolbar belong to the table, search
 * filters rows without a round trip, selecting rows reveals the batch actions, and a row
 * itself is the edit affordance.
 */
@customElement("cofy-module-list")
export class CofyModuleList extends LitElement {
  public static override styles = css`
    :host {
      display: block;
    }
    cds-table-row {
      cursor: pointer;
    }
    .secondary {
      color: var(--cds-text-secondary);
    }
  `;

  @consume({ context: moduleStoreContext, subscribe: true })
  public store!: ModuleStore;

  @property({ type: String }) public slug = "";

  @state() private deleting = false;
  @state() private deleteError: ProblemError | null = null;

  public readonly stateController = new StateController(this);

  public override willUpdate(changed: Map<string, unknown>): void {
    if ((changed.has("slug") || changed.has("store")) && this.slug !== "" && this.store !== undefined) {
      void this.store.ensure(this.slug);
    }
  }

  public override render(): TemplateResult | typeof nothing {
    if (this.store === undefined) return nothing;

    const modules = this.store.list(this.slug);
    if (modules === undefined) {
      return this.store.error !== null
        ? html`<cofy-problem-details .problem=${this.store.error}></cofy-problem-details>`
        : html`<cds-table-skeleton row-count="3" column-count="3"></cds-table-skeleton>`;
    }

    // Deliberately not `is-sortable`: Carbon sorts by reordering the row elements in the
    // DOM, which moves nodes Lit owns and corrupts its child-part boundaries - the next
    // render then empties the table. Sorting here would have to sort the data instead.
    return html`
      ${this.deleteError === null
        ? nothing
        : html`<cofy-problem-details .problem=${this.deleteError}></cofy-problem-details>`}

      <cds-table is-selectable @cds-table-row-selected=${(): void => this.onSelectionChange()}>
        <cds-table-header-title slot="title">Modules</cds-table-header-title>
        <cds-table-header-description slot="description">
          What this community collects, computes and serves.
        </cds-table-header-description>

        <cds-table-toolbar slot="toolbar">
          <cds-table-batch-actions>
            <cds-button ?disabled=${this.deleting} @click=${(): void => void this.deleteSelected()}>
              ${this.deleting ? "Deleting…" : "Delete"}
            </cds-button>
          </cds-table-batch-actions>
          <cds-table-toolbar-content>
            <cds-table-toolbar-search placeholder="Search modules"></cds-table-toolbar-search>
            <cds-button @click=${(): void => this.requestCreate()}>Add module</cds-button>
          </cds-table-toolbar-content>
        </cds-table-toolbar>

        <cds-table-head>
          <cds-table-header-row>
            <cds-table-header-cell>Module</cds-table-header-cell>
            <cds-table-header-cell>Type</cds-table-header-cell>
          </cds-table-header-row>
        </cds-table-head>
        <cds-table-body>${modules.map((module): TemplateResult => this.row(module))}</cds-table-body>
      </cds-table>
    `;
  }

  private row(module: ModuleSettings): TemplateResult {
    return html`
      <cds-table-row
        selection-name=${moduleKey(module)}
        @click=${(event: MouseEvent): void => this.onRowClick(event, module)}
      >
        <cds-table-cell>
          <div>${module.display_name || module.name}</div>
          ${module.description === null || module.description === undefined
            ? nothing
            : html`<div class="secondary">${module.description}</div>`}
        </cds-table-cell>
        <cds-table-cell><cds-tag type="cool-gray">${module.type}</cds-tag></cds-table-cell>
      </cds-table-row>
    `;
  }

  /**
   * A click on the row opens it, except when it landed on the selection checkbox.
   *
   * The checkbox lives in the row's shadow DOM and its click is composed, so it reaches this
   * handler too - selecting a row would otherwise navigate away from the list.
   */
  private onRowClick(event: MouseEvent, module: ModuleSettings): void {
    const onCheckbox = event
      .composedPath()
      .some((target) => target instanceof HTMLElement && target.localName === "cds-checkbox");
    if (onCheckbox) return;

    this.dispatchEvent(
      new CustomEvent("module-edit", {
        detail: { slug: this.slug, id: { type: module.type, name: module.name } },
        bubbles: true,
        composed: true,
      }),
    );
  }

  private requestCreate(): void {
    this.dispatchEvent(new CustomEvent("module-create", { detail: { slug: this.slug }, bubbles: true, composed: true }));
  }

  /** Clear the error banner as soon as the selection changes, so it cannot outlive its cause. */
  private onSelectionChange(): void {
    this.deleteError = null;
  }

  private selectedModules(): ModuleSettings[] {
    const selected = new Set(
      Array.from(this.renderRoot.querySelectorAll("cds-table-row"))
        .filter((row) => row.hasAttribute("selected"))
        .map((row) => row.getAttribute("selection-name")),
    );
    return (this.store.list(this.slug) ?? []).filter((module) => selected.has(moduleKey(module)));
  }

  /**
   * Delete every selected module, after asking once.
   *
   * Sequential rather than concurrent: the API serializes writes to a community anyway, and
   * stopping at the first failure leaves a clearer picture than a partial fan-out would.
   */
  private async deleteSelected(): Promise<void> {
    const modules = this.selectedModules();
    if (modules.length === 0) return;

    const [first] = modules;
    const question =
      modules.length === 1
        ? `Delete ${first!.display_name || first!.name}? Its configuration cannot be recovered.`
        : `Delete ${modules.length} modules? Their configuration cannot be recovered.`;
    if (!window.confirm(question)) return;

    this.deleting = true;
    this.deleteError = null;
    try {
      for (const module of modules) {
        await this.store.remove(this.slug, { type: module.type, name: module.name });
      }
    } catch (error) {
      this.deleteError = error as ProblemError;
    } finally {
      this.deleting = false;
    }
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-module-list": CofyModuleList;
  }
}
