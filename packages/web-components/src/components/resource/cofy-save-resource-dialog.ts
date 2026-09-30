import { consume } from "@lit/context";
import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { ProblemError, ResourceStore } from "@cofy/frontend-sdk";

import "@awesome.me/webawesome/dist/components/button/button.js";
import "@awesome.me/webawesome/dist/components/dialog/dialog.js";
import "@awesome.me/webawesome/dist/components/input/input.js";
import "../cofy-problem-details.js";

import { CofyElement } from "../../cofy-element.js";
import { communitySlugContext, resourceStoreContext } from "../../context.js";
import { utilityStyles } from "../../theme/utility-styles.js";

/**
 * Saves a value as a new resource of `kind`, asking only for its name and description.
 *
 * Opened and closed by its host through `open`: it reports `resource-saved` with the new
 * resource's name once stored, and `dialog-closed` when dismissed without saving.
 */
@customElement("cofy-save-resource-dialog")
export class CofySaveResourceDialog extends CofyElement {
  public static override styles = [
    utilityStyles,
    css`
      :host {
        display: contents;
      }
    `,
  ];

  @consume({ context: resourceStoreContext, subscribe: true })
  @state()
  public resourceStore?: ResourceStore;

  @consume({ context: communitySlugContext, subscribe: true })
  @state()
  public slug = "";

  @property({ type: Boolean }) public open = false;
  @property({ type: String }) public kind = "";
  @property({ attribute: false }) public value: unknown;

  @state() private name = "";
  @state() private description = "";
  @state() private saving = false;
  @state() private error: ProblemError | null = null;

  public override willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("open") && this.open) {
      this.name = "";
      this.description = "";
      this.error = null;
    }
  }

  public override render(): TemplateResult {
    return html`
      <wa-dialog
        label=${this.t("saveResource.title")}
        ?open=${this.open}
        @wa-hide=${(event: Event): void => this.onHide(event)}
      >
        <div class="wa-stack">
          ${this.error === null ? nothing : html`<cofy-problem-details .problem=${this.error}></cofy-problem-details>`}
          <wa-input
            label=${this.t("saveResource.name")}
            hint=${this.t("saveResource.nameHint")}
            required
            .value=${this.name}
            @input=${(event: Event): void => {
              this.name = (event.target as HTMLElement & { value?: string }).value ?? "";
            }}
          ></wa-input>
          <wa-input
            label=${this.t("saveResource.description")}
            .value=${this.description}
            @input=${(event: Event): void => {
              this.description = (event.target as HTMLElement & { value?: string }).value ?? "";
            }}
          ></wa-input>
        </div>
        <wa-button slot="footer" appearance="plain" @click=${(): void => this.close()}>
          ${this.t("saveResource.cancel")}
        </wa-button>
        <wa-button
          slot="footer"
          variant="brand"
          ?disabled=${this.name === "" || this.saving}
          @click=${(): void => void this.save()}
        >
          ${this.saving ? this.t("saveResource.saving") : this.t("saveResource.save")}
        </wa-button>
      </wa-dialog>
    `;
  }

  private async save(): Promise<void> {
    if (this.resourceStore === undefined) return;

    this.saving = true;
    this.error = null;
    try {
      const created = await this.resourceStore.create(this.slug, {
        type: this.kind,
        name: this.name,
        description: this.description === "" ? null : this.description,
        value: this.value,
      });
      this.dispatchEvent(
        new CustomEvent("resource-saved", { detail: { name: created.name }, bubbles: true, composed: true }),
      );
    } catch (error) {
      this.error = error as ProblemError;
    } finally {
      this.saving = false;
    }
  }

  /** The dialog closing itself - Escape, its close button - rather than a nested element hiding. */
  private onHide(event: Event): void {
    if (event.target !== event.currentTarget) return;
    this.close();
  }

  private close(): void {
    this.dispatchEvent(new CustomEvent("dialog-closed", { bubbles: true, composed: true }));
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-save-resource-dialog": CofySaveResourceDialog;
  }
}
