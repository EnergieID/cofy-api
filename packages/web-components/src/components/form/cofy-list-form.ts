import { css, html } from "lit";
import type { TemplateResult } from "lit";
import { customElement, state } from "lit/decorators.js";

import "@awesome.me/webawesome/dist/components/accordion/accordion.js";
import "@awesome.me/webawesome/dist/components/accordion-item/accordion-item.js";
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

/**
 * An array's elements, each a collapsible `wa-accordion-item` labelled with its own position
 * and a delete link, so a long list does not mean a long page - only the item being worked on
 * needs to stay open. An item's own body is a bare `cofy-any-form` (no card of its own): the
 * accordion item's outline is already its visual boundary.
 *
 * The last item is not a real one: it is the "Add" affordance, styled and behaving like the
 * others (same trigger, a `+` instead of the expand chevron) but wired to append a fresh
 * element instead of expanding - see {@link onExpand}.
 *
 * Which items are open is this component's own state (`expandedIndices`), not the accordion's:
 * `?expanded=` is bound to it on every render, and `wa-expand`/`wa-collapse` keep it in sync
 * with whatever the reader does by hand, so a re-render for an unrelated reason (typing in some
 * other field) never fights what is currently open. Adding an element seeds its index into that
 * same set, which is what opens it immediately - no separate one-shot mechanism needed.
 */
@customElement("cofy-list-form")
export class CofyListForm extends CofyFormField {
  public static override styles = [
    nativeStyles,
    utilityStyles,
    css`
      :host {
        display: block;
      }
    `,
  ];

  @state() private expandedIndices: ReadonlySet<number> = new Set();

  public override render(): TemplateResult {
    const node = deref(this.schema, this.root);
    const itemsSchema = isRecord(node["items"]) ? node["items"] : {};
    const items = Array.isArray(this.value) ? this.value : [];
    const label = this.bare ? "" : fieldLabel(node, this.pointer);
    const ownIssues = this.bare ? [] : issuesAt(this.issues, this.pointer);

    return html`
      <cofy-field-shell data-pointer=${this.pointer} label=${label} .issues=${ownIssues}>
        <wa-accordion
          appearance="outlined"
          @wa-expand=${(event: CustomEvent<{ item: Element }>): void => this.onExpand(event, itemsSchema)}
          @wa-collapse=${(event: CustomEvent<{ item: Element }>): void => this.onCollapse(event)}
        >
          ${items.map((item, index) => this.renderItem(item, index, itemsSchema))}
          <wa-accordion-item class="cofy-list-add" label=${this.t("form.add")}>
            <wa-icon slot="icon" name="plus" library="cofy"></wa-icon>
          </wa-accordion-item>
        </wa-accordion>
      </cofy-field-shell>
    `;
  }

  private renderItem(item: unknown, index: number, itemsSchema: Record<string, unknown>): TemplateResult {
    return html`
      <wa-accordion-item data-segment=${index} ?expanded=${this.expandedIndices.has(index)}>
        <div slot="label" class="wa-split">
          <span>${index + 1}</span>
          <a
            class="wa-link-plain"
            role="button"
            tabindex="0"
            @click=${(event: MouseEvent): void => {
              // Without this the trigger's own click handler also fires and toggles the item.
              event.stopPropagation();
              this.removeAt(index);
            }}
            @keydown=${(event: KeyboardEvent): void => {
              if (event.key !== "Enter" && event.key !== " ") return;
              event.preventDefault();
              event.stopPropagation();
              this.removeAt(index);
            }}
          >
            ${this.t("form.remove")}
          </a>
        </div>
        <cofy-any-form
          .schema=${itemsSchema}
          .root=${this.root}
          .pointer=${pointerFor(this.pointer, index)}
          .value=${item}
          .issues=${this.issues}
          bare
        ></cofy-any-form>
      </wa-accordion-item>
    `;
  }

  /** The "Add" item is a fake: cancel its own expand and append a fresh element instead. */
  private onExpand(event: CustomEvent<{ item: Element }>, itemsSchema: Record<string, unknown>): void {
    if (event.detail.item.classList.contains("cofy-list-add")) {
      event.preventDefault();
      this.add(itemsSchema);
      return;
    }
    this.setExpanded(event.detail.item, true);
  }

  private onCollapse(event: CustomEvent<{ item: Element }>): void {
    this.setExpanded(event.detail.item, false);
  }

  private setExpanded(target: Element, expanded: boolean): void {
    const index = Number((target as HTMLElement).dataset["segment"]);
    if (Number.isNaN(index)) return;

    const next = new Set(this.expandedIndices);
    if (expanded) next.add(index);
    else next.delete(index);
    this.expandedIndices = next;
  }

  private add(itemsSchema: Record<string, unknown>): void {
    const items: unknown[] = Array.isArray(this.value) ? this.value : [];
    this.expandedIndices = new Set([...this.expandedIndices, items.length]);
    const value = [...items, seedFromSchema(itemsSchema, this.root)];
    this.dispatchEvent(
      new CustomEvent("field-change", { bubbles: true, composed: true, detail: { pointer: this.pointer, value } }),
    );
  }

  private removeAt(index: number): void {
    const items: unknown[] = Array.isArray(this.value) ? this.value : [];
    const value = items.filter((_, i) => i !== index);

    // Every later index shifts down by one along with its element; carry each one's open state
    // with it rather than leaving it keyed to a position that now holds something else.
    const shifted = new Set<number>();
    for (const expandedIndex of this.expandedIndices) {
      if (expandedIndex < index) shifted.add(expandedIndex);
      else if (expandedIndex > index) shifted.add(expandedIndex - 1);
    }
    this.expandedIndices = shifted;

    this.dispatchEvent(
      new CustomEvent("field-change", { bubbles: true, composed: true, detail: { pointer: this.pointer, value } }),
    );
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-list-form": CofyListForm;
  }
}
