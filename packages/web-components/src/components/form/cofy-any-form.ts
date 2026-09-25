import { consume } from "@lit/context";
import { css, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, state } from "lit/decorators.js";
import { html, unsafeStatic } from "lit/static-html.js";

import "./cofy-yaml-form.js";
import "../layout/cofy-link-button.js";

import { fieldRegistryContext } from "../../context.js";
import type { AS_YAML_OPTION, FieldRegistry } from "./field-registry.js";
import { defaultFieldRegistry } from "./field-registry.js";
import { CofyFormField } from "./form-field.js";
import { deref } from "./schema/ref.js";
import { resolveNode } from "./schema/resolve.js";
import { fieldDescription, fieldLabel } from "./schema/summary.js";
import { nativeStyles } from "../../theme/native-styles.js";
import { utilityStyles } from "../../theme/utility-styles.js";

const YAML_TAG = "cofy-yaml-form";

/**
 * Renders whichever field a schema node calls for: the first mapper in {@link fieldRegistryContext}
 * whose `matches` accepts this field's own schema, falling back to `cofy-yaml-form` if none do -
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
  public static override styles = [
    nativeStyles,
    utilityStyles,
    css`
      :host {
        display: contents;
      }
    `,
  ];

  @consume({ context: fieldRegistryContext, subscribe: true })
  public fieldRegistry: FieldRegistry = defaultFieldRegistry;

  @state() private yamlToggle = false;

  private shouldShowYaml(asYaml: AS_YAML_OPTION): boolean {
    switch (asYaml){
      case "never": return false;
      case "optional": return this.yamlToggle;
      case "default": return !this.yamlToggle;
    }
  }

  public override render(): TemplateResult {
    const node = resolveNode(this.schema, this.root);
    const shallow = deref(this.schema, this.root);

    const match = this.fieldRegistry.getFirstMatch(node, this.root);
    const asYaml = match?.asYaml ?? "never";
    const tag = this.shouldShowYaml(asYaml) ? YAML_TAG : match?.tag ?? YAML_TAG
    const tagName = unsafeStatic(tag);

    const yamlToggle = html`<cofy-link-button
      slot="actions"
      @click=${(): void => {
        this.yamlToggle = !this.yamlToggle;
      }}
    >
      ${this.shouldShowYaml(asYaml) ? this.t("form.viewAsForm") : this.t("form.viewAsYaml")}
    </cofy-link-button>`;

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
    >
      ${asYaml != "never" ? yamlToggle : nothing }
    </${tagName}>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-any-form": CofyAnyForm;
  }
}
