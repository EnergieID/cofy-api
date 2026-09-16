import { consume } from "@lit/context";
import { css } from "lit";
import type { TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";
import { html, unsafeStatic } from "lit/static-html.js";

import { fieldRegistryContext } from "../../context.js";
import { defaultFieldRegistry, type FieldRegistry } from "./custom-fields.js";
import { CofyFormField } from "./form-field.js";
import { resolveFieldKind, schemaTypeName, type FieldKind } from "./schema-dispatch.js";

const KIND_TAG: Record<FieldKind["kind"], string> = {
  union: "cofy-union-form",
  enum: "cofy-enum-form",
  const: "cofy-const-form",
  secret: "cofy-secret-form",
  string: "cofy-string-form",
  number: "cofy-number-form",
  boolean: "cofy-boolean-form",
  object: "cofy-object-form",
  array: "cofy-list-form",
  unknown: "cofy-unknown-form",
};

/**
 * Renders whichever field a schema node calls for.
 *
 * The one place a schema type name is checked against a registered custom field before
 * falling through to the generic dispatch - see {@link FieldRegistry}.
 */
@customElement("cofy-any-form")
export class CofyAnyForm extends CofyFormField {
  public static override styles = css`
    :host {
      display: contents;
    }
  `;

  @consume({ context: fieldRegistryContext, subscribe: true })
  public fieldRegistry: FieldRegistry = defaultFieldRegistry;

  public override render(): TemplateResult {
    const custom = this.fieldRegistry.customFieldFor(schemaTypeName(this.schema));
    const kind = resolveFieldKind(this.schema, this.root);
    const tag = unsafeStatic(custom ?? KIND_TAG[kind.kind]);

    // A container kind (object/array/union/enum/unknown) needs the schema resolveFieldKind
    // actually resolved to - $ref-followed and, for an `Optional[X]`, unwrapped past its
    // `anyOf` - or its own `properties`/`items`/`oneOf` would be one level too deep for it to
    // see, since each field's own render() only ever calls the cheaper `deref()` on top of
    // whatever schema it is handed. A leaf kind (string/number/...) carries no such structure
    // to lose, so the original schema - title and description included - passes through as is.
    const schema = "schema" in kind ? kind.schema : this.schema;

    return html`<${tag}
      .schema=${schema}
      .root=${this.root}
      .pointer=${this.pointer}
      .value=${this.value}
      ?required=${this.required}
      .issues=${this.issues}
      .hide=${this.hide}
      ?bare=${this.bare}
    ></${tag}>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-any-form": CofyAnyForm;
  }
}
