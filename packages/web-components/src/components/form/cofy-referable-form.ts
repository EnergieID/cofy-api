import { consume } from "@lit/context";
import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, state } from "lit/decorators.js";
import { repeat } from "lit/directives/repeat.js";
import type { JsonSchema, Referable, ResourceRef, ResourceSettings, ResourceStore } from "@cofy/frontend-sdk";

import "@awesome.me/webawesome/dist/components/option/option.js";
import "@awesome.me/webawesome/dist/components/select/select.js";
import "./cofy-action-menu.js";
import "./cofy-any-form.js";
import "./cofy-field-shell.js";
import "../resource/cofy-save-resource-dialog.js";

import { communitySlugContext, fieldRegistryContext, resourceStoreContext } from "../../context.js";
import { utilityStyles } from "../../theme/utility-styles.js";
import type { MenuAction } from "./cofy-action-menu.js";
import type { FieldRegistry } from "./field-registry.js";
import { defaultFieldRegistry } from "./field-registry.js";
import { CofyFormField } from "./form-field.js";
import { seedFromSchema } from "./schema/defaults.js";
import { isRefValue, referableBranches, referableOf } from "./schema/referable.js";
import { resolveNode } from "./schema/resolve.js";

/** What a secret's value reads as once stored - the value itself is never sent back. */
const MASK = "**********";

/**
 * A field whose value can also be a reference to a resource (an `x-referable` schema): edited as
 * its value, with using a resource instead - or saving the value as one - among its actions.
 *
 * Which of the two it shows follows from the value itself: a reference shows the resource
 * picker, anything else the value's own form. Switching to a resource keeps the value it
 * replaces, so switching back restores it.
 */
@customElement("cofy-referable-form")
export class CofyReferableForm extends CofyFormField {
  public static override styles = [
    utilityStyles,
    css`
      :host {
        display: block;
      }
    `,
  ];

  @consume({ context: resourceStoreContext, subscribe: true })
  @state()
  public resourceStore?: ResourceStore;

  @consume({ context: communitySlugContext, subscribe: true })
  @state()
  public slug = "";

  @consume({ context: fieldRegistryContext, subscribe: true })
  public fieldRegistry: FieldRegistry = defaultFieldRegistry;

  @state() private saving = false;

  /** The value a reference replaced, restored when a value is specified again. */
  private replaced: unknown;

  public override willUpdate(changed: Map<string, unknown>): void {
    if ((changed.has("slug") || changed.has("resourceStore")) && this.slug !== "") {
      void this.resourceStore?.ensure(this.slug);
    }
  }

  public override render(): TemplateResult {
    const referable = referableOf(this.schema);
    const branches = referableBranches(this.schema);
    if (referable === undefined || branches === undefined) return html``;

    return isRefValue(this.value) ? this.renderRef(this.value, referable, branches.value) : this.renderValue(referable, branches.value);
  }

  private renderValue(referable: Referable, schema: JsonSchema): TemplateResult {
    const actions: MenuAction[] = [];
    // Only offered once there is something to pick.
    if ((this.resourceStore?.fitting(this.slug, referable).length ?? 0) > 0) {
      actions.push({ id: "use-resource", label: this.t("form.useResource"), run: (): void => this.useResource() });
    }
    if (this.canSave(referable)) {
      actions.push({
        id: "save-as-resource",
        label: this.t("form.saveAsResource"),
        run: (): void => {
          this.saving = true;
        },
      });
    }

    // A container shows the actions beside its own label; a single input - a field offering no
    // YAML view - has no place for them, so its label and the actions beside it are drawn here.
    const leaf =
      actions.length > 0 && this.fieldRegistry.getFirstMatch(resolveNode(schema, this.root), this.root)?.asYaml === undefined;
    const form = html`<cofy-any-form
      .schema=${schema}
      .root=${this.root}
      .pointer=${this.pointer}
      .value=${this.value}
      ?required=${this.required && !leaf}
      .issues=${this.issues}
      .hide=${this.hide}
      ?bare=${this.bare || leaf}
      .label=${this.label}
      .description=${this.description}
      .menuActions=${leaf ? [] : actions}
    ></cofy-any-form>`;

    return html`
      ${leaf && !this.bare
        ? html`<cofy-field-shell label=${this.requiredLabel()}>
            <cofy-action-menu slot="actions" .actions=${actions}></cofy-action-menu>
            ${form}
          </cofy-field-shell>`
        : form}
      <cofy-save-resource-dialog
        .open=${this.saving}
        .kind=${referable.kind}
        .value=${this.value}
        @resource-saved=${(event: CustomEvent<{ name: string }>): void => this.onSaved(event.detail.name)}
        @dialog-closed=${(): void => {
          this.saving = false;
        }}
      ></cofy-save-resource-dialog>
    `;
  }

  private renderRef(ref: ResourceRef, referable: Referable, valueSchema: JsonSchema): TemplateResult {
    const options = this.resourceStore?.fitting(this.slug, referable) ?? [];
    // No label of its own: it always sits under the field's, which names what it picks.
    const picker = html`<wa-select
      class="wa-flex-grow"
      aria-label=${this.label || this.t("form.resource")}
      placeholder=${this.t("form.chooseResource")}
      .value=${ref.name}
      lang=${this.i18n?.resolvedLanguage ?? "en"}
      @change=${(event: Event): void => this.onChoose(event)}
    >
      ${repeat(
        options,
        (resource) => resource.name,
        (resource) => html`<wa-option value=${resource.name}>${this.optionLabel(resource)}</wa-option>`,
      )}
    </wa-select>`;
    const menu = html`<cofy-action-menu
      slot="actions"
      .actions=${[
        { id: "specify-value", label: this.t("form.specifyValue"), run: (): void => this.specifyValue(valueSchema) },
      ]}
    ></cofy-action-menu>`;

    return html`
      <cofy-field-shell
        data-pointer=${this.pointer}
        label=${this.bare ? "" : this.requiredLabel()}
        description=${this.bare ? "" : this.description}
        .issues=${this.refIssues()}
      >
        ${this.bare
          ? html`<div class="wa-cluster wa-align-items-center">${picker}${menu}</div>`
          : html`${menu}${picker}`}
        ${options.length === 0
          ? html`<span class="wa-caption-s">${this.t("form.noResources", { kind: referable.kind })}</span>`
          : nothing}
      </cofy-field-shell>
    `;
  }

  /** The field's label, marked the way a required control marks its own, for the control drawn under it without one. */
  private requiredLabel(): string {
    return this.required ? `${this.label}*` : this.label;
  }

  /** A secret already stored comes back masked, so there is no value to save as a resource. */
  private canSave(referable: Referable): boolean {
    if (this.resourceStore === undefined || this.value === undefined || this.value === null) return false;
    return !(referable.kind === "secret" && this.value === MASK);
  }

  /** The reference's own issues, and those of its name - it has no form of its own to show them in. */
  private refIssues(): readonly { message: string }[] {
    if (this.bare) return [];
    return this.issues.filter((issue) => issue.pointer === this.pointer || issue.pointer.startsWith(`${this.pointer}/`));
  }

  private optionLabel(resource: ResourceSettings): string {
    return resource.description ? `${resource.name} — ${resource.description}` : resource.name;
  }

  private useResource(): void {
    this.replaced = this.value;
    this.emit({ type: "ref", name: "" });
  }

  private specifyValue(schema: JsonSchema): void {
    const value = this.replaced ?? seedFromSchema(schema, this.root);
    this.replaced = undefined;
    this.emit(value);
  }

  private onSaved(name: string): void {
    this.saving = false;
    this.replaced = this.value;
    this.emit({ type: "ref", name });
  }

  private onChoose(event: Event): void {
    const name = (event.target as HTMLElement & { value?: string }).value ?? "";
    this.emit({ type: "ref", name });
  }

  private emit(value: unknown): void {
    this.dispatchEvent(
      new CustomEvent("field-change", { bubbles: true, composed: true, detail: { pointer: this.pointer, value } }),
    );
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-referable-form": CofyReferableForm;
  }
}
