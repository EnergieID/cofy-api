import { consume } from "@lit/context";
import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { ProblemError, ResourceSettings, ResourceStore, ResourceUsages } from "@cofy/frontend-sdk";

import "@awesome.me/webawesome/dist/components/button/button.js";
import "@awesome.me/webawesome/dist/components/skeleton/skeleton.js";
import "@awesome.me/webawesome/dist/components/tag/tag.js";

import { CofyElement } from "../../cofy-element.js";
import { resourceStoreContext } from "../../context.js";
import { tableStyles } from "../../theme/table.js";
import { utilityStyles } from "../../theme/utility-styles.js";
import "../layout/cofy-heading.js";
import "../cofy-problem-details.js";

/**
 * The resources configured in a community: values configured once and referenced by name.
 *
 * Laid out like `cofy-module-list`. Deleting first asks what still references the resource,
 * since the server refuses to delete one that is in use.
 */
@customElement("cofy-resource-list")
export class CofyResourceList extends CofyElement {
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

  @consume({ context: resourceStoreContext, subscribe: true })
  @state()
  public store!: ResourceStore;

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

    const resources = this.store.list(this.slug);
    const error = this.deleteError ?? this.store.error;

    if (error != null) return html`<cofy-problem-details .problem=${error}></cofy-problem-details>`;
    if (resources === undefined) {
      return html`<div class="wa-stack">
        ${Array.from({ length: 4 }, () => html`<wa-skeleton></wa-skeleton>`)}
      </div>`;
    }

    return html`
      <div class="wa-stack">
        <cofy-heading>
          <span slot="title">${this.t("resourceList.title")}</span>
          <span slot="description">${this.t("resourceList.description")}</span>
          <wa-button slot="actions" variant="brand" @click=${(): void => this.requestCreate()}>
            ${this.t("resourceList.add")}
          </wa-button>
        </cofy-heading>

        <table>
          <thead>
            <tr>
              <th scope="col">${this.t("resourceList.columns.resource")}</th>
              <th scope="col">${this.t("resourceList.columns.kind")}</th>
              <th scope="col">${this.t("resourceList.columns.description")}</th>
              <th scope="col" class="actions"><span class="wa-visually-hidden">${this.t("resourceList.columns.actions")}</span></th>
            </tr>
          </thead>
          <tbody>
            ${resources.length === 0
              ? html`<tr class="empty">
                  <td class="secondary" colspan="4">${this.t("resourceList.empty")}</td>
                </tr>`
              : resources.map((resource): TemplateResult => this.row(resource))}
          </tbody>
        </table>
      </div>
    `;
  }

  /** A row opens its resource; the button in it deletes. Keyboard handling as in `cofy-module-list`. */
  private row(resource: ResourceSettings): TemplateResult {
    return html`
      <tr
        data-key=${resource.name}
        tabindex="0"
        @click=${(): void => this.requestEdit(resource)}
        @keydown=${(event: KeyboardEvent): void => this.onKeydown(event, resource)}
      >
        <td>${resource.name}</td>
        <td><wa-tag variant="neutral" appearance="outlined">${resource.type}</wa-tag></td>
        <td class="secondary">${resource.description ?? ""}</td>
        <td class="actions">
          <wa-button
            appearance="plain"
            size="small"
            ?disabled=${this.deleting}
            @click=${(event: MouseEvent): void => {
              // Without this the row's own handler would also fire and navigate away.
              event.stopPropagation();
              void this.deleteResource(resource);
            }}
          >
            ${this.deleting ? this.t("resourceList.deleting") : this.t("resourceList.delete")}
          </wa-button>
        </td>
      </tr>
    `;
  }

  private onKeydown(event: KeyboardEvent, resource: ResourceSettings): void {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    this.requestEdit(resource);
  }

  private requestEdit(resource: ResourceSettings): void {
    this.dispatchEvent(
      new CustomEvent("resource-edit", {
        detail: { slug: this.slug, name: resource.name },
        bubbles: true,
        composed: true,
      }),
    );
  }

  private requestCreate(): void {
    this.dispatchEvent(new CustomEvent("resource-create", { detail: { slug: this.slug }, bubbles: true, composed: true }));
  }

  /** Delete one resource, after telling what still references it, or asking. */
  private async deleteResource(resource: ResourceSettings): Promise<void> {
    this.deleting = true;
    this.deleteError = null;
    try {
      const users = this.users(await this.store.usages(this.slug, resource.name));
      if (users.length > 0) {
        window.alert(this.t("resourceList.inUse", { name: resource.name, users: users.join(", ") }));
        return;
      }
      if (!window.confirm(this.t("resourceList.deleteConfirm", { name: resource.name }))) return;
      await this.store.remove(this.slug, resource.name);
    } catch (error) {
      this.deleteError = error as ProblemError;
    } finally {
      this.deleting = false;
    }
  }

  private users(usages: ResourceUsages): string[] {
    return [...usages.modules.map((module) => `${module.type}:${module.name}`), ...usages.resources];
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-resource-list": CofyResourceList;
  }
}
