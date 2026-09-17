import { consume } from "@lit/context";
import { css } from "lit";
import type { TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";
import { html, unsafeStatic } from "lit/static-html.js";

import "./cofy-unknown-form.js";

import { fieldRegistryContext } from "../../context.js";
import type { FieldRegistry } from "./field-registry.js";
import { defaultFieldRegistry } from "./field-registry.js";
import { CofyFormField } from "./form-field.js";
import { deref } from "./schema/ref.js";
import { resolveNode } from "./schema/resolve.js";
import { fieldDescription, fieldLabel } from "./schema/summary.js";

const UNKNOWN_TAG = "cofy-unknown-form";

/**
 * Renders whichever field a schema node calls for: the first mapper in {@link fieldRegistryContext}
 * whose `matches` accepts this field's own schema, falling back to `cofy-unknown-form` if none do -
 * imported here directly, since this is the one place that fallback tag is named.
 *
 * The one place a field's label/description are read off its schema - resolved past its own
 * `$ref` but no further (`deref`, cheap - a field's `title`/`description` sit on the schema
 * exactly as the property declares it, not on whatever an `Optional[X]`'s inner branch resolves
 * to) - and handed down as props, so a leaf/container never has to derive either itself. Every
 * mounted tag also gets the same, fully resolved `.schema` (`resolveNode`, computed separately),
 * regardless of which one it is.
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
    const node = resolveNode(this.schema, this.root);
    const shallow = deref(this.schema, this.root);
    const tagName = unsafeStatic(this.fieldRegistry.getTag(node, this.root) ?? UNKNOWN_TAG);

    return html`<${tagName}
      .schema=${node}
      .root=${this.root}
      .pointer=${this.pointer}
      .value=${this.value}
      ?required=${this.required}
      .issues=${this.issues}
      .hide=${this.hide}
      ?bare=${this.bare}
      .label=${fieldLabel(shallow, this.pointer)}
      .description=${fieldDescription(shallow)}
    ></${tagName}>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-any-form": CofyAnyForm;
  }
}
