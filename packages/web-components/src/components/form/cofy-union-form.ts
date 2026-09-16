import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";
import { repeat } from "lit/directives/repeat.js";
import type { JsonSchema } from "@cofy/frontend-sdk";

import "@awesome.me/webawesome/dist/components/card/card.js";
import "@awesome.me/webawesome/dist/components/option/option.js";
import "@awesome.me/webawesome/dist/components/select/select.js";
import "./cofy-any-form.js";
import "./cofy-field-shell.js";

import { seedFromSchema } from "../../schema-defaults.js";
import { deref, isRecord } from "../../schema-ref.js";
import { nativeStyles } from "../../theme/native-styles.js";
import { utilityStyles } from "../../theme/utility-styles.js";
import { fieldLabel } from "./field-shell.js";
import { CofyFormField } from "./form-field.js";
import { issuesAt } from "./issues.js";
import { resolveFieldKind, schemaTypeName, type Discriminator } from "./schema-dispatch.js";

/**
 * A `oneOf`/multi-branch `anyOf` field: its own label and card, a branch picker inside it, then
 * the chosen branch's own fields, also inside - a union is always grouped in one card, whatever
 * it resolves to. When that branch is itself an object (the common case), it renders without a
 * card of its own (`bare`): this card already is its visual boundary.
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
    `,
  ];

  public override render(): TemplateResult {
    const kind = resolveFieldKind(this.schema, this.root);
    if (kind.kind !== "union") return html``;

    const ownIssues = issuesAt(this.issues, this.pointer);
    const picker = kind.discriminator
      ? this.renderDiscriminated(kind.discriminator)
      : this.renderBareChoice(kind.branches);
    const branch = this.resolveChosenBranch(kind.discriminator, kind.branches);

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
              .hide=${kind.discriminator ? [kind.discriminator.propertyName] : []}
              bare
            ></cofy-any-form>`}
      </div>
    `;

    return html`
      <cofy-field-shell
        data-pointer=${this.pointer}
        label=${fieldLabel(deref(this.schema, this.root), this.pointer)}
        .issues=${ownIssues}
      >
        <wa-card appearance="outlined">${body}</wa-card>
      </cofy-field-shell>
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
          (option) => html`<wa-option value=${option}>${readable(option)}</wa-option>`,
        )}
      </wa-select>
    `;
  }

  private renderBareChoice(branches: readonly JsonSchema[]): TemplateResult {
    const selected =
      this.value === undefined || this.value === null ? undefined : branches[matchBranch(this.value, branches, this.root)];

    return html`
      <wa-select
        label=${this.t("form.type")}
        placeholder=${this.t("form.choose")}
        .value=${selected === undefined ? "" : (schemaTypeName(selected) ?? "")}
        lang=${this.i18n?.resolvedLanguage ?? "en"}
        ?required=${this.required}
        @change=${(event: Event): void => this.chooseBranch(event, branches)}
      >
        ${repeat(
          branches,
          (branch) => schemaTypeName(branch) ?? "",
          (branch) => html`<wa-option value=${schemaTypeName(branch) ?? ""}>${readable(schemaTypeName(branch) ?? "?")}</wa-option>`,
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
    const typeName = (event.target as HTMLElement & { value?: string }).value ?? "";
    const branch = branches.find((candidate) => schemaTypeName(candidate) === typeName);
    if (branch === undefined) return;
    this.emit(seedFromSchema(branch, this.root));
  }

  private emit(value: unknown): void {
    this.dispatchEvent(
      new CustomEvent("field-change", { bubbles: true, composed: true, detail: { pointer: this.pointer, value } }),
    );
  }
}

/**
 * A best-effort guess at which branch *value* already matches. Defaults to the first.
 *
 * A branch whose own `const`-tagged property matches the value's is preferred - that is what a
 * `kind`/`type`-style tag actually looks like once resolved, and it is far more specific than
 * "has the same required keys," which every sibling branch sharing a common field would also
 * satisfy (a `kind: "index"` value still lists `kind` as a required key of every other branch).
 */
function matchBranch(value: unknown, branches: readonly JsonSchema[], root: JsonSchema): number {
  if (!isRecord(value)) return 0;

  const byTag = branches.findIndex((branch) => {
    const properties = deref(branch, root)["properties"];
    if (!isRecord(properties)) return false;
    return Object.entries(properties).some(
      ([key, propSchema]) => isRecord(propSchema) && "const" in propSchema && value[key] === propSchema["const"],
    );
  });
  if (byTag !== -1) return byTag;

  const byRequired = branches.findIndex((branch) => {
    const required = deref(branch, root)["required"];
    return Array.isArray(required) && required.length > 0 && required.every((key) => key in value);
  });
  return byRequired === -1 ? 0 : byRequired;
}

function readable(tag: string): string {
  return tag.replace(/_/g, " ");
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-union-form": CofyUnionForm;
  }
}
