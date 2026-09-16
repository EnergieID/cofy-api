import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";

import "@awesome.me/webawesome/dist/components/accordion/accordion.js";
import "@awesome.me/webawesome/dist/components/accordion-item/accordion-item.js";
import "@awesome.me/webawesome/dist/components/card/card.js";
import "@awesome.me/webawesome/dist/components/icon/icon.js";
import "./cofy-any-form.js";
import "./cofy-field-shell.js";
import "../../icons.js";

import { seedFromSchema } from "../../schema-defaults.js";
import { deref, isRecord } from "../../schema-ref.js";
import { nativeStyles } from "../../theme/native-styles.js";
import { utilityStyles } from "../../theme/utility-styles.js";
import { fieldLabel } from "./field-shell.js";
import { CofyFormField } from "./form-field.js";
import { issuesAt } from "./issues.js";
import { pointerFor } from "./pointer.js";
import { resolveFieldKind } from "./schema-dispatch.js";

/**
 * An object's own properties, each rendered by a child `cofy-any-form`.
 *
 * A property whose kind is `object` and whose value is absent renders as a label plus a fake
 * "Add" accordion item - the same affordance `cofy-list-form` uses for an empty list - instead
 * of recursing straight in. This is the one gate this family needs against a cyclic schema (a
 * `directive` source can wrap another `directive`, unbounded): nothing is ever expanded except
 * in response to a real click, one level at a time.
 *
 * A nested object (anywhere but the document root) draws its own label and card, like any
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
    `,
  ];

  public override render(): TemplateResult {
    const node = deref(this.schema, this.root);
    const properties = node["properties"];
    const required = new Set(Array.isArray(node["required"]) ? (node["required"] as string[]) : []);
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

    // A union's own card already shows the issue reported at this pointer for a bare branch.
    const ownIssues = this.bare ? [] : issuesAt(this.issues, this.pointer);

    return html`
      <cofy-field-shell
        data-pointer=${this.pointer}
        label=${wrapped ? fieldLabel(node, this.pointer) : ""}
        .issues=${ownIssues}
      >
        ${wrapped ? html`<wa-card appearance="outlined">${propertiesBlock}</wa-card>` : propertiesBlock}
      </cofy-field-shell>
    `;
  }

  private renderProperty(name: string, propSchema: Record<string, unknown>, required: boolean): TemplateResult {
    const childPointer = pointerFor(this.pointer, name);
    const childValue = isRecord(this.value) ? this.value[name] : undefined;
    const kind = resolveFieldKind(propSchema, this.root);
    const empty = childValue === undefined || childValue === null;

    if (kind.kind === "object" && empty) {
      return html`
        <cofy-field-shell data-pointer=${childPointer} data-segment=${name} label=${fieldLabel(kind.schema, childPointer)}>
          <wa-accordion
            appearance="outlined"
            @wa-expand=${(event: CustomEvent<{ item: Element }>): void => {
              event.preventDefault();
              this.addAt(childPointer, propSchema);
            }}
          >
            <wa-accordion-item label=${this.t("form.add")}>
              <wa-icon slot="icon" name="plus" library="cofy"></wa-icon>
            </wa-accordion-item>
          </wa-accordion>
        </cofy-field-shell>
      `;
    }

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

  private addAt(pointer: string, schema: Record<string, unknown>): void {
    const value = seedFromSchema(schema, this.root);
    this.dispatchEvent(
      new CustomEvent("field-change", { bubbles: true, composed: true, detail: { pointer, value } }),
    );
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-object-form": CofyObjectForm;
  }
}
