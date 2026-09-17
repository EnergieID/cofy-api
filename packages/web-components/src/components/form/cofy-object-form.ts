import { consume } from "@lit/context";
import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";

import "@awesome.me/webawesome/dist/components/details/details.js";
import "@awesome.me/webawesome/dist/components/icon/icon.js";
import "./cofy-any-form.js";
import "./cofy-field-shell.js";
import "../../icons.js";

import { fieldRegistryContext } from "../../context.js";
import { nativeStyles } from "../../theme/native-styles.js";
import { utilityStyles } from "../../theme/utility-styles.js";
import type { FieldRegistry } from "./field-registry.js";
import { defaultFieldRegistry } from "./field-registry.js";
import { CofyFormField } from "./form-field.js";
import { seedFromSchema } from "./schema/defaults.js";
import { pointerFor } from "./schema/pointer.js";
import { isRecord } from "./schema/ref.js";

/**
 * An object's own properties, each rendered by a child `cofy-any-form`.
 *
 * An absent value renders as a label plus a fake "Create" details item - the same affordance
 * `cofy-list-form` uses for an empty list's own "Add" - instead of recursing into properties
 * that do not exist yet. This is the one gate this family needs against a cyclic schema (a
 * `directive` source can wrap another `directive`, unbounded): a cyclic property is always
 * absent until a real click creates it, so nothing is ever expanded except in response to one,
 * one level at a time. Each property is handed to its own `cofy-any-form` regardless of kind or
 * value - this gate is `cofy-object-form`'s own concern, not something a parent has to know to
 * check first.
 *
 * A populated, non-required value can be deleted back to that same absent state, through a link
 * in the details' own header - not offered when `required`, since deleting a required field
 * would leave the document invalid with no schema-driven way back except re-creating it.
 *
 * A nested object (anywhere but the document root) draws its own label and details, like any
 * other field - unless `bare`, meaning the ancestor that mounted it (a union, around the
 * branch it resolved to) already drew both, and drawing them again would double up.
 */
@customElement("cofy-object-form")
export class CofyObjectForm extends CofyFormField {
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
    if (this.value === undefined || this.value === null) return this.renderEmpty();

    const properties = this.schema["properties"];
    const required = new Set(Array.isArray(this.schema["required"]) ? (this.schema["required"] as string[]) : []);
    const wrapped = this.pointer !== "" && !this.bare;

    const propertiesBlock = html`
      <div class="wa-stack">
        ${isRecord(properties)
          ? Object.entries(properties)
              .filter((entry): entry is [string, Record<string, unknown>] => isRecord(entry[1]) && !this.hide.includes(entry[0]))
              .map(([name, propSchema]) => this.renderProperty(name, propSchema, required.has(name)))
          : nothing}
      </div>
    `;

    return html`
      <cofy-field-shell
        data-pointer=${this.pointer}
        label=${wrapped ? this.label : ""}
        description=${wrapped ? this.description : ""}
        .issues=${this.ownIssues}
      >
        ${wrapped ? this.renderPopulated(propertiesBlock) : propertiesBlock}
      </cofy-field-shell>
    `;
  }

  private renderPopulated(content: TemplateResult): TemplateResult {
    const summary = this.fieldRegistry.getSummary(this.schema, this.root, this.value);

    return html`
      <wa-details appearance="outlined" open>
        <div slot="summary" class="wa-split">
          <span>${summary ?? ""}</span>
          ${this.required
            ? nothing
            : html`<a
                class="wa-link-plain"
                role="button"
                tabindex="0"
                @click=${(event: MouseEvent): void => {
                  event.stopPropagation();
                  this.clear();
                }}
                @keydown=${(event: KeyboardEvent): void => {
                  if (event.key !== "Enter" && event.key !== " ") return;
                  event.preventDefault();
                  event.stopPropagation();
                  this.clear();
                }}
              >
                ${this.t("form.remove")}
              </a>`}
        </div>
        ${content}
      </wa-details>
    `;
  }

  private renderProperty(name: string, propSchema: Record<string, unknown>, required: boolean): TemplateResult {
    const childPointer = pointerFor(this.pointer, name);
    const childValue = isRecord(this.value) ? this.value[name] : undefined;

    return html`
      <cofy-any-form
        data-segment=${name}
        .schema=${propSchema}
        .root=${this.root}
        .pointer=${childPointer}
        .value=${childValue}
        ?required=${required}
        .issues=${this.issues}
      ></cofy-any-form>
    `;
  }

  private renderEmpty(): TemplateResult {
    return html`
      <cofy-field-shell data-pointer=${this.pointer} label=${this.label} description=${this.description}>
        <wa-details
          appearance="outlined"
          summary=${this.t("form.create")}
          @wa-show=${(event: CustomEvent): void => {
            event.preventDefault();
            this.add();
          }}
        >
          <wa-icon slot="expand-icon" name="plus" library="cofy"></wa-icon>
        </wa-details>
      </cofy-field-shell>
    `;
  }

  private add(): void {
    const value = seedFromSchema(this.schema, this.root);
    this.dispatchEvent(
      new CustomEvent("field-change", { bubbles: true, composed: true, detail: { pointer: this.pointer, value } }),
    );
  }

  private clear(): void {
    this.dispatchEvent(
      new CustomEvent("field-change", { bubbles: true, composed: true, detail: { pointer: this.pointer, value: null } }),
    );
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-object-form": CofyObjectForm;
  }
}
