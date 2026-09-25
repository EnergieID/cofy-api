import { consume } from "@lit/context";
import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { moduleKey, type ModuleSettings, type ModuleStore, type ProblemError } from "@cofy/frontend-sdk";

import "@awesome.me/webawesome/dist/components/button/button.js";
import "@awesome.me/webawesome/dist/components/skeleton/skeleton.js";
import "@awesome.me/webawesome/dist/components/tag/tag.js";

import { CofyElement } from "../../cofy-element.js";
import { moduleStoreContext } from "../../context.js";
import { tableStyles } from "../../theme/table.js";
import { utilityStyles } from "../../theme/utility-styles.js";
import "../layout/cofy-heading.js";
import "../cofy-problem-details.js";

/**
 * The modules configured in a community.
 *
 * A row is the edit affordance and carries its own delete button. Deliberately plain: there is
 * no selection model, no search and no sorting, because none of them are needed at the volumes
 * a community actually holds. Search is the likeliest of the three to be wanted first, and is
 * a `filter()` over the rows here when it is - no store or API change.
 */
@customElement("cofy-module-list")
export class CofyModuleList extends CofyElement {
  public static override styles = [
    tableStyles,
    utilityStyles,
    css`
      :host {
        display: block;
      }
      th.actions,
      td.actions {
        inline-size: 1%;
        white-space: nowrap;
        text-align: end;
      }
    `,
  ];

  @consume({ context: moduleStoreContext, subscribe: true })
  @state()
  public store!: ModuleStore;

  @property({ type: String }) public slug = "";

  @state() private deleting = false;
  @state() private deleteError: ProblemError | null = null;

  public override willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("slug") || changed.has("store")) {
      if (this.slug !== "") void this.store?.ensure(this.slug);
    }
  }

  public override render(): TemplateResult | typeof nothing {
    if (this.store === undefined) return nothing;

    const modules = this.store.list(this.slug);
    const error = this.deleteError ?? this.store.error;

    if (error != null) return html`<cofy-problem-details .problem=${error}></cofy-problem-details>`;
    if (modules === undefined) {
      return html`<div class="wa-stack">
        ${Array.from({ length: 4 }, () => html`<wa-skeleton></wa-skeleton>`)}
      </div>`;
    }

    return html`
      <div class="wa-stack">
        <cofy-heading>
          <span slot="title">${this.t("moduleList.title")}</span>
          <span slot="description">${this.t("moduleList.description")}</span>
          <wa-button slot="actions" variant="brand" @click=${(): void => this.requestCreate()}>
            ${this.t("moduleList.add")}
          </wa-button>
        </cofy-heading>

        <table>
          <thead>
            <tr>
              <th scope="col">${this.t("moduleList.columns.module")}</th>
              <th scope="col">${this.t("moduleList.columns.type")}</th>
              <th scope="col" class="actions"></th>
            </tr>
          </thead>
          <tbody>
            ${modules.length === 0
              ? html`<tr class="empty">
                  <td class="secondary" colspan="3">${this.t("moduleList.empty")}</td>
                </tr>`
              : modules.map((module): TemplateResult => this.row(module))}
          </tbody>
        </table>
      </div>
    `;
  }

  /**
   * A row opens its module; the button in it deletes.
   *
   * `<tr>` is not focusable of its own accord the way a framework's row component is, so the
   * keyboard handling here is what keeps the list usable without a mouse.
   */
  private row(module: ModuleSettings): TemplateResult {
    return html`
      <tr
        data-key=${moduleKey(module)}
        tabindex="0"
        @click=${(): void => this.requestEdit(module)}
        @keydown=${(event: KeyboardEvent): void => this.onKeydown(event, module)}
      >
        <td>${module.display_name || module.name}</td>
        <td><wa-tag variant="neutral" appearance="outlined">${module.type}</wa-tag></td>
        <td class="actions">
          <wa-button
            appearance="plain"
            size="small"
            ?disabled=${this.deleting}
            @click=${(event: MouseEvent): void => {
              // Without this the row's own handler would also fire and navigate away.
              event.stopPropagation();
              void this.deleteModule(module);
            }}
          >
            ${this.deleting ? this.t("moduleList.deleting") : this.t("moduleList.delete")}
          </wa-button>
        </td>
      </tr>
    `;
  }

  private onKeydown(event: KeyboardEvent, module: ModuleSettings): void {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    this.requestEdit(module);
  }

  private requestEdit(module: ModuleSettings): void {
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

  /** Delete one module, after asking. */
  private async deleteModule(module: ModuleSettings): Promise<void> {
    const question = this.t("moduleList.deleteConfirm", { name: module.display_name || module.name });
    if (!window.confirm(question)) return;

    this.deleting = true;
    this.deleteError = null;
    try {
      await this.store.remove(this.slug, { type: module.type, name: module.name });
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
