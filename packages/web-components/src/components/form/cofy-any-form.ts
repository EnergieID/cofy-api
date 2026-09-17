import { consume } from "@lit/context";
import { css } from "lit";
import type { TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";
import { html, unsafeStatic } from "lit/static-html.js";

import "./cofy-unknown-form.js";

import { fieldRegistryContext } from "../../context.js";
import type { FieldRegistry } from "./field-registry.js";
import { defaultFieldRegistry } from "./field-registry.js";
import { fieldMeta } from "./field-shell.js";
import { CofyFormField } from "./form-field.js";
import { resolveNode } from "./schema-dispatch.js";

const UNKNOWN_TAG = "cofy-unknown-form";

/**
 * Renders whichever field a schema node calls for: the first mapper in {@link fieldRegistryContext}
 * whose `matches` accepts this field's own schema, falling back to `cofy-unknown-form` if none do -
 * imported here directly, since this is the one place that fallback tag is named.
 *
 * The one place a field's label/description are read off its schema (`fieldMeta`, computed once
 * per render from *this* field's own schema, before it is resolved) and handed down as props -
 * every mounted tag gets the same, fully resolved `.schema` (`resolveNode`, also computed once)
 * regardless of which one it is, so a leaf/container never has to resolve or extract either
 * itself.
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
    const { label, description } = fieldMeta(this.schema, this.root, this.pointer);
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
      .label=${label}
      .description=${description}
    ></${tagName}>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-any-form": CofyAnyForm;
  }
}
