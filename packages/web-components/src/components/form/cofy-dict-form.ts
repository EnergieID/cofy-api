import { consume } from "@lit/context";
import { css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement, state } from "lit/decorators.js";

import "@awesome.me/webawesome/dist/components/accordion/accordion.js";
import "@awesome.me/webawesome/dist/components/accordion-item/accordion-item.js";
import "@awesome.me/webawesome/dist/components/icon/icon.js";
import "@awesome.me/webawesome/dist/components/input/input.js";
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
 * A `dict[str, X]` schema's own entries (`additionalProperties`, no fixed `properties`), each a
 * collapsible `wa-accordion-item` labelled `key: value summary` with a delete link - the same
 * shape `cofy-list-form` uses for an array, keyed by string instead of position. An entry's own
 * body renders its key first, editable in place (renaming rewrites the entry, since no
 * `cofy-any-form` of its own could otherwise address a property name), then the value - a bare
 * `cofy-any-form` for `additionalProperties`, since the accordion item is already its own visual
 * boundary.
 *
 * The last item is not a real one, exactly as in `cofy-list-form`: the "Add" affordance, same
 * trigger and a `+` instead of the expand chevron, wired to append a fresh entry under a
 * generated unique key instead of expanding - see {@link onExpand}.
 *
 * Which entries are open is tracked by key, not position (`expandedKeys`): unlike an array index,
 * a key survives a sibling being removed, so there is no shifting to do - only a rename needs to
 * carry its entry's open state over to the new key.
 */
@customElement("cofy-dict-form")
export class CofyDictForm extends CofyFormField {
  public static override styles = [
    nativeStyles,
    utilityStyles,
    css`
      :host {
        display: block;
      }
    `,
  ];

  @consume({ context: fieldRegistryContext, subscribe: true })
  public fieldRegistry: FieldRegistry = defaultFieldRegistry;

  @state() private expandedKeys: ReadonlySet<string> = new Set();

  public override render(): TemplateResult {
    const valueSchema = isRecord(this.schema["additionalProperties"]) ? this.schema["additionalProperties"] : {};
    const entries = isRecord(this.value) ? this.value : {};
    const label = this.bare ? "" : this.label;
    const description = this.bare ? "" : this.description;

    return html`
      <cofy-field-shell data-pointer=${this.pointer} label=${label} description=${description} .issues=${this.ownIssues}>
        <wa-accordion
          appearance="outlined"
          @wa-expand=${(event: CustomEvent<{ item: Element }>): void => this.onExpand(event, valueSchema)}
          @wa-collapse=${(event: CustomEvent<{ item: Element }>): void => this.onCollapse(event)}
        >
          ${Object.entries(entries).map(([key, value]) => this.renderEntry(key, value, valueSchema))}
          <wa-accordion-item class="cofy-dict-add" label=${this.t("form.add")}>
            <wa-icon slot="icon" name="plus" library="cofy"></wa-icon>
          </wa-accordion-item>
        </wa-accordion>
      </cofy-field-shell>
    `;
  }

  private renderEntry(key: string, value: unknown, valueSchema: Record<string, unknown>): TemplateResult {
    const summary = this.fieldRegistry.getSummary(valueSchema, this.root, value);

    return html`
      <wa-accordion-item data-segment=${key} ?expanded=${this.expandedKeys.has(key)}>
        <div slot="label" class="wa-split">
          <span>${key}${summary ? html`: ${summary}` : ""}</span>
          <a
            class="wa-link-plain"
            role="button"
            tabindex="0"
            @click=${(event: MouseEvent): void => {
              // Without this the trigger's own click handler also fires and toggles the item.
              event.stopPropagation();
              this.removeKey(key);
            }}
            @keydown=${(event: KeyboardEvent): void => {
              if (event.key !== "Enter" && event.key !== " ") return;
              event.preventDefault();
              event.stopPropagation();
              this.removeKey(key);
            }}
          >
            ${this.t("form.remove")}
          </a>
        </div>
        <div class="wa-stack">
          <wa-input label=${this.t("form.key")} .value=${key} @input=${(event: Event): void => this.renameKey(key, event)}></wa-input>
          <cofy-any-form
            .schema=${valueSchema}
            .root=${this.root}
            .pointer=${pointerFor(this.pointer, key)}
            .value=${value}
            .issues=${this.issues}
            bare
          ></cofy-any-form>
        </div>
      </wa-accordion-item>
    `;
  }

  /** The "Add" item is a fake: cancel its own expand and append a fresh entry instead. */
  private onExpand(event: CustomEvent<{ item: Element }>, valueSchema: Record<string, unknown>): void {
    event.stopPropagation();
    if (event.detail.item.classList.contains("cofy-dict-add")) {
      event.preventDefault();
      this.add(valueSchema);
      return;
    }
    this.setExpanded(event.detail.item, true);
  }

  private onCollapse(event: CustomEvent<{ item: Element }>): void {
    event.stopPropagation();
    this.setExpanded(event.detail.item, false);
  }

  private setExpanded(target: Element, expanded: boolean): void {
    const key = (target as HTMLElement).dataset["segment"];
    if (key === undefined) return;

    const next = new Set(this.expandedKeys);
    if (expanded) next.add(key);
    else next.delete(key);
    this.expandedKeys = next;
  }

  private add(valueSchema: Record<string, unknown>): void {
    const entries = isRecord(this.value) ? this.value : {};
    const key = this.nextKey(entries);
    this.expandedKeys = new Set([...this.expandedKeys, key]);
    const value = { ...entries, [key]: seedFromSchema(valueSchema, this.root) };
    this.dispatchEvent(
      new CustomEvent("field-change", { bubbles: true, composed: true, detail: { pointer: this.pointer, value } }),
    );
  }

  private removeKey(key: string): void {
    const entries = isRecord(this.value) ? this.value : {};
    const value = Object.fromEntries(Object.entries(entries).filter(([k]) => k !== key));

    const next = new Set(this.expandedKeys);
    next.delete(key);
    this.expandedKeys = next;

    this.dispatchEvent(
      new CustomEvent("field-change", { bubbles: true, composed: true, detail: { pointer: this.pointer, value } }),
    );
  }

  private renameKey(oldKey: string, event: Event): void {
    const newKey = (event.target as HTMLElement & { value?: string }).value ?? "";
    if (newKey === oldKey) return;

    const entries = isRecord(this.value) ? this.value : {};
    // Never silently merge two entries into one - leave the rename unapplied until the reader
    // picks a key that is not already someone else's.
    if (newKey in entries) return;

    const value = Object.fromEntries(Object.entries(entries).map(([k, v]) => [k === oldKey ? newKey : k, v]));

    const next = new Set(this.expandedKeys);
    if (next.has(oldKey)) {
      next.delete(oldKey);
      next.add(newKey);
    }
    this.expandedKeys = next;

    this.dispatchEvent(
      new CustomEvent("field-change", { bubbles: true, composed: true, detail: { pointer: this.pointer, value } }),
    );
  }

  /** The next generated key not already in *entries* - `"key"`, then `"key1"`, `"key2"`, ... */
  private nextKey(entries: Record<string, unknown>): string {
    if (!("key" in entries)) return "key";
    let n = 1;
    while (`key${n}` in entries) n += 1;
    return `key${n}`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-dict-form": CofyDictForm;
  }
}
