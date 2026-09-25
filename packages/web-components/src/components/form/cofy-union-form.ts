import { consume } from "@lit/context";
import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";
import { repeat } from "lit/directives/repeat.js";
import type { JsonSchema } from "@cofy/frontend-sdk";

import "@awesome.me/webawesome/dist/components/details/details.js";
import "@awesome.me/webawesome/dist/components/option/option.js";
import "@awesome.me/webawesome/dist/components/select/select.js";
import "./cofy-any-form.js";
import "./cofy-field-shell.js";
import "../layout/cofy-link-button.js";

import { fieldRegistryContext } from "../../context.js";
import { nativeStyles } from "../../theme/native-styles.js";
import { utilityStyles } from "../../theme/utility-styles.js";
import type { FieldRegistry } from "./field-registry.js";
import { defaultFieldRegistry } from "./field-registry.js";
import { CofyFormField } from "./form-field.js";
import { isRecord } from "./schema/ref.js";
import { seedFromSchema } from "./schema/defaults.js";
import {
  discriminatorOf,
  matchBranch,
  schemaTypeName,
  unionBranches,
  type Discriminator,
} from "./schema/resolve.js";
import { titleCase } from "./schema/summary.js";

/**
 * A `oneOf`/multi-branch `anyOf` field: its own label and details, a branch picker inside it,
 * then the chosen branch's own fields, also inside - a union is always grouped in one collapsible
 * details, whatever it resolves to. When that branch is itself an object (the common case), it
 * renders without a details of its own (`bare`): this one already is its visual boundary.
 *
 * `bare` also suppresses this union's *own* label/details, the same way `cofy-object-form` treats
 * it - needed when a list/union mounts this as one of ITS OWN elements (a list of a union type,
 * say): the accordion item/outer details is already that element's boundary, so a second one here
 * would double up.
 *
 * A chosen, non-required branch can be cleared back to unchosen through a link in the details'
 * own header - not offered when `required`, since clearing a required field would leave the
 * document invalid with no schema-driven way back except choosing a branch again.
 *
 * The discriminator case (pydantic's `Field(discriminator=...)`) drives the picker from the
 * value's own tag property. The no-discriminator case - `energy_cost.Formula`, tagged by a
 * callable discriminator pydantic cannot express as `discriminator.mapping` - falls back to a
 * plain branch picker with a best-effort guess at which branch an existing value matches;
 * `validate()` stays the source of truth for correctness, this only decides what the picker
 * shows pre-selected.
 */
@customElement("cofy-union-form")
export class CofyUnionForm extends CofyFormField {
  public static override styles = [
    nativeStyles,
    utilityStyles,
    css`
      :host {
        display: block;
      }
      [slot="summary"] {
        flex: 1;
      }
    `,
  ];

  @consume({ context: fieldRegistryContext, subscribe: true })
  public fieldRegistry: FieldRegistry = defaultFieldRegistry;

  public override render(): TemplateResult {
    const branches = unionBranches(this.schema, this.root);
    if (branches === undefined) return html``;

    const discriminator = discriminatorOf(this.schema);
    const picker = discriminator ? this.renderDiscriminated(discriminator) : this.renderBareChoice(branches);
    const branch = this.resolveChosenBranch(discriminator, branches);

    const body = html`
      <div class="wa-stack">
        ${picker}
        ${branch === undefined
          ? nothing
          : html`<cofy-any-form
              .schema=${branch}
              .root=${this.root}
              .pointer=${this.pointer}
              .value=${this.value}
              ?required=${this.required}
              .issues=${this.issues}
              .hide=${discriminator ? [discriminator.propertyName] : []}
              bare
            ></cofy-any-form>`}
      </div>
    `;

    return html`
      <cofy-field-shell
        data-pointer=${this.pointer}
        label=${this.bare ? "" : this.label}
        description=${this.bare ? "" : this.description}
        .issues=${this.ownIssues}
      >
        <slot name="actions" slot="actions"></slot>
        ${this.bare ? body : this.renderDetails(body, branch !== undefined)}
      </cofy-field-shell>
    `;
  }

  private renderDetails(body: TemplateResult, chosen: boolean): TemplateResult {
    const summary = this.fieldRegistry.getSummary(this.schema, this.root, this.value);

    return html`
      <wa-details appearance="outlined" open>
        <div slot="summary" class="wa-split">
          <span>${summary ?? ""}</span>
          ${chosen && !this.required
            ? html`<cofy-link-button @click=${(): void => this.emit(null)}>${this.t("form.remove")}</cofy-link-button>`
            : nothing}
        </div>
        ${body}
      </wa-details>
    `;
  }

  private renderDiscriminated(discriminator: Discriminator): TemplateResult {
    const tag = isRecord(this.value) ? this.value[discriminator.propertyName] : undefined;
    const options = Object.keys(discriminator.mapping);

    return html`
      <wa-select
        label=${this.t("form.type")}
        placeholder=${this.t("form.choose")}
        .value=${typeof tag === "string" ? tag : ""}
        lang=${this.i18n?.resolvedLanguage ?? "en"}
        ?required=${this.required}
        @change=${(event: Event): void => this.chooseTag(event, discriminator)}
      >
        ${repeat(
          options,
          (option) => option,
          (option) => html`<wa-option value=${option}>${titleCase(option)}</wa-option>`,
        )}
      </wa-select>
    `;
  }
  
  private optionValue(branch: JsonSchema, index: number): string {
    return schemaTypeName(branch) ?? String(index);
  }

  private renderBareChoice(branches: readonly JsonSchema[]): TemplateResult {
    const selectedIndex =
      this.value === undefined || this.value === null ? undefined : matchBranch(this.value, branches, this.root);

    return html`
      <wa-select
        label=${this.t("form.type")}
        placeholder=${this.t("form.choose")}
        .value=${selectedIndex === undefined ? "" : this.optionValue(branches[selectedIndex]!, selectedIndex)}
        lang=${this.i18n?.resolvedLanguage ?? "en"}
        ?required=${this.required}
        @change=${(event: Event): void => this.chooseBranch(event, branches)}
      >
        ${repeat(
          branches,
          (branch, index) => this.optionValue(branch, index),
          (branch, index) => html`<wa-option value=${this.optionValue(branch, index)}
            >${titleCase(schemaTypeName(branch) ?? String(index + 1))}</wa-option
          >`,
        )}
      </wa-select>
    `;
  }

  /** The schema to hand to the child `cofy-any-form`, or `undefined` while nothing is chosen yet. */
  private resolveChosenBranch(discriminator: Discriminator | undefined, branches: readonly JsonSchema[]): JsonSchema | undefined {
    if (discriminator) {
      const tag = isRecord(this.value) ? this.value[discriminator.propertyName] : undefined;
      const ref = typeof tag === "string" ? discriminator.mapping[tag] : undefined;
      return ref === undefined ? undefined : { $ref: ref };
    }
    if (this.value === undefined || this.value === null) return undefined;
    return branches[matchBranch(this.value, branches, this.root)];
  }

  private chooseTag(event: Event, discriminator: Discriminator): void {
    const tag = (event.target as HTMLElement & { value?: string }).value ?? "";
    const ref = discriminator.mapping[tag];
    if (ref === undefined) return;
    this.emit(seedFromSchema({ $ref: ref }, this.root));
  }

  private chooseBranch(event: Event, branches: readonly JsonSchema[]): void {
    const value = (event.target as HTMLElement & { value?: string }).value ?? "";
    const branch = branches.find((candidate, index) => this.optionValue(candidate, index) === value);
    if (branch === undefined) return;
    this.emit(seedFromSchema(branch, this.root));
  }

  private emit(value: unknown): void {
    this.dispatchEvent(
      new CustomEvent("field-change", { bubbles: true, composed: true, detail: { pointer: this.pointer, value } }),
    );
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-union-form": CofyUnionForm;
  }
}
