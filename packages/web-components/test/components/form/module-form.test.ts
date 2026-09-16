import { beforeEach, describe, expect, it } from "vitest";
import { ContextProvider } from "@lit/context";
import type { ReactiveControllerHost } from "lit";
import type { AllowedModule, JsonSchema, ValidationIssue } from "@cofy/frontend-sdk";

import "../../../src/components/form/register.js";
import "../../../src/components/module/cofy-module-form.js";
import { i18nContext } from "../../../src/context.js";
import type { CofyObjectForm } from "../../../src/components/form/cofy-object-form.js";
import type { CofyModuleForm } from "../../../src/components/module/cofy-module-form.js";
import { testI18n } from "../../support/i18n.js";

/**
 * Provides i18n the way the real app does - `<cofy-app>` provides it once, and every
 * component several shadow roots deep consumes it through that one ancestor. Setting `.i18n`
 * directly on just the mounted element (the alternative) only reaches that one element's own
 * `t()` calls, not the recursive tree of children Lit creates beneath it.
 */
async function provideI18n(element: ReactiveControllerHost & HTMLElement): Promise<void> {
  new ContextProvider(element, { context: i18nContext, initialValue: await testI18n() });
}

/**
 * A schema exercising every dispatch case: const, string, optional string (anyOf), number,
 * boolean, enum (via $ref), secret, a discriminated union whose second branch cycles into
 * itself directly (an object-level cycle, gated by a fake Add accordion item), a bare oneOf with no
 * discriminator (the `energy_cost.Formula` shape - a union-level cycle, self-gating because a
 * fresh branch's value is null until chosen), and both a scalar and a union-typed array.
 */
const schema: JsonSchema = {
  type: "object",
  properties: {
    type: { const: "demo", default: "demo", type: "string" },
    name: { type: "string", title: "Name" },
    display_name: { anyOf: [{ type: "string" }, { type: "null" }], default: null, title: "Display Name" },
    count: { type: "integer", title: "Count" },
    active: { type: "boolean", title: "Active" },
    level: { $ref: "#/$defs/Level" },
    source: {
      title: "Source",
      discriminator: { propertyName: "type", mapping: { a: "#/$defs/SourceA", b: "#/$defs/SourceB" } },
      oneOf: [{ $ref: "#/$defs/SourceA" }, { $ref: "#/$defs/SourceB" }],
    },
    formula: { $ref: "#/$defs/Formula" },
    tags: { type: "array", items: { type: "string" }, title: "Tags" },
  },
  required: ["type", "name", "source", "formula"],
  $defs: {
    Level: { title: "Level", enum: ["low", "high"] },
    SourceA: {
      title: "SourceA",
      type: "object",
      properties: {
        type: { const: "a", default: "a", type: "string" },
        api_key: { type: "string", format: "password", writeOnly: true, title: "Api Key" },
      },
      required: ["type", "api_key"],
    },
    SourceB: {
      title: "SourceB",
      type: "object",
      properties: {
        type: { const: "b", default: "b", type: "string" },
        nested: { $ref: "#/$defs/SourceB" },
      },
      required: ["type", "nested"],
    },
    Formula: { title: "Formula", oneOf: [{ $ref: "#/$defs/IndexFormula" }, { $ref: "#/$defs/MinimumFormula" }] },
    IndexFormula: {
      title: "IndexFormula",
      type: "object",
      properties: { kind: { const: "index", default: "index", type: "string" } },
      required: ["kind"],
    },
    MinimumFormula: {
      title: "MinimumFormula",
      type: "object",
      properties: {
        kind: { const: "minimum", default: "minimum", type: "string" },
        minimum: { type: "array", items: { $ref: "#/$defs/Formula" } },
      },
      required: ["kind", "minimum"],
    },
  },
};

const value = {
  type: "demo",
  name: "spot",
  source: { type: "a", api_key: "secret" },
  formula: { kind: "index" },
  tags: ["one", "two"],
};

async function mountObjectForm(
  overrides: Partial<{ value: unknown; issues: ValidationIssue[] }> = {},
): Promise<CofyObjectForm> {
  const element = document.createElement("cofy-object-form");
  await provideI18n(element);
  element.schema = schema;
  element.root = schema;
  element.pointer = "";
  element.value = overrides.value ?? value;
  element.issues = overrides.issues ?? [];
  document.body.append(element);
  await element.updateComplete;
  // The tree mounts several levels of custom element recursively; a child created during a
  // parent's render does not finish its own first render within the parent's updateComplete.
  await new Promise((resolve) => setTimeout(resolve, 0));
  return element;
}

/**
 * Every field in the family lives in its own shadow root a few levels below the one that
 * mounted it (`cofy-object-form` -> `cofy-any-form` -> the concrete field), so a plain
 * `querySelector` from the top cannot see it. This walks light-DOM descendants at each level
 * and follows any shadow root it finds, exactly the way a real user's assistive tech would.
 */
function deepQuery(root: ParentNode, selector: string): HTMLElement | null {
  const direct = root.querySelector<HTMLElement>(selector);
  if (direct !== null) return direct;

  for (const element of Array.from(root.querySelectorAll<HTMLElement>("*"))) {
    const shadow = element.shadowRoot;
    if (shadow === null) continue;
    const found = deepQuery(shadow, selector);
    if (found !== null) return found;
  }
  return null;
}

/**
 * Every match for *selector* in *root*'s whole composed subtree - root's own shadow root (if
 * it has one), every descendant's shadow root, and the light-DOM descendants (including
 * slotted content) along the way. Needed once a piece of markup a test used to find with a
 * plain `querySelector` (back when it was inlined by a render function) moves inside a real
 * child element's own shadow root instead.
 */
function deepQueryAll(root: Element | ShadowRoot, selector: string): HTMLElement[] {
  const found: HTMLElement[] = [...root.querySelectorAll<HTMLElement>(selector)];

  const shadow = "shadowRoot" in root ? root.shadowRoot : null;
  if (shadow !== null) found.push(...deepQueryAll(shadow, selector));

  for (const element of Array.from(root.querySelectorAll<HTMLElement>("*"))) {
    if (element.shadowRoot !== null) found.push(...deepQueryAll(element.shadowRoot, selector));
  }
  return found;
}

function fieldAt(element: HTMLElement, pointer: string): HTMLElement | null {
  return deepQuery(element.shadowRoot!, `[data-pointer="${pointer}"]`);
}

function select(element: HTMLElement, pointer: string): HTMLElement & { value: string } {
  return fieldAt(element, pointer)!.querySelector("wa-select") as HTMLElement & { value: string };
}

describe("the generic form family, mounted end to end", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("renders the type discriminator as a read-only const, not an input", async () => {
    const element = await mountObjectForm();

    const field = fieldAt(element, "/type")!;
    expect(field.querySelector("wa-input, wa-select, wa-checkbox")).toBeNull();
    expect(field.textContent).toContain("demo");
  });

  it("renders a plain string field bound to its value", async () => {
    const element = await mountObjectForm();

    const input = fieldAt(element, "/name")!.querySelector<HTMLElement & { value: string }>("wa-input")!;
    expect(input.value).toBe("spot");
  });

  it("renders an optional (anyOf-nullable) string as a plain input, not a union picker", async () => {
    const element = await mountObjectForm();

    const field = fieldAt(element, "/display_name")!;
    expect(field.querySelector("wa-select")).toBeNull();
    expect(field.querySelector("wa-input")).not.toBeNull();
  });

  it("renders a number field as a numeric wa-input", async () => {
    const element = await mountObjectForm({ value: { ...value, count: 3 } });

    const input = fieldAt(element, "/count")!.querySelector<HTMLElement & { value: string; type: string }>("wa-input")!;
    expect(input.type).toBe("number");
    expect(input.value).toBe("3");
  });

  it("renders a boolean field as a checkbox", async () => {
    const element = await mountObjectForm({ value: { ...value, active: true } });

    const checkbox = fieldAt(element, "/active")!.querySelector<HTMLElement & { checked: boolean }>("wa-checkbox")!;
    expect(checkbox.checked).toBe(true);
  });

  it("renders an enum (reached through a $ref) as a select of its values", async () => {
    const element = await mountObjectForm({ value: { ...value, level: "high" } });

    const options = fieldAt(element, "/level")!.querySelectorAll("wa-option");
    expect(Array.from(options).map((o) => o.getAttribute("value"))).toEqual(["low", "high"]);
  });

  it("renders a password/writeOnly field as a masked input", async () => {
    const element = await mountObjectForm();

    const input = fieldAt(element, "/source/api_key")!.querySelector<HTMLElement & { type: string }>("wa-input")!;
    expect(input.type).toBe("password");
  });

  it("renders a scalar array as one accordion item per element, plus a trailing Add item", async () => {
    const element = await mountObjectForm();

    const field = fieldAt(element, "/tags")!;
    expect(field.querySelectorAll("cofy-any-form")).toHaveLength(2);
    expect(field.querySelectorAll("wa-accordion-item")).toHaveLength(3);
  });

  it("adding an array element seeds a new default and dispatches the whole new array", async () => {
    const element = await mountObjectForm();
    const events: unknown[] = [];
    element.addEventListener("field-change", (event) => events.push((event as CustomEvent).detail));

    // The "Add" item cancels its own wa-expand and appends instead - see onExpand().
    const accordion = fieldAt(element, "/tags")!.querySelector("wa-accordion")!;
    const addItem = accordion.querySelector(".cofy-list-add")!;
    accordion.dispatchEvent(new CustomEvent("wa-expand", { detail: { item: addItem }, cancelable: true }));

    expect(events).toEqual([{ pointer: "/tags", value: ["one", "two", ""] }]);
  });

  it("removing an array element dispatches the array without it", async () => {
    const element = await mountObjectForm();
    const events: unknown[] = [];
    element.addEventListener("field-change", (event) => events.push((event as CustomEvent).detail));

    const remove = fieldAt(element, "/tags")!.querySelector<HTMLElement>('[slot="label"] a')!;
    remove.dispatchEvent(new MouseEvent("click"));

    expect(events).toEqual([{ pointer: "/tags", value: ["two"] }]);
  });

  it("removes an array element from the keyboard too - the delete link has no native href to make it tabbable", async () => {
    const element = await mountObjectForm();
    const events: unknown[] = [];
    element.addEventListener("field-change", (event) => events.push((event as CustomEvent).detail));

    const remove = fieldAt(element, "/tags")!.querySelector<HTMLElement>('[slot="label"] a')!;
    expect(remove.getAttribute("tabindex")).toBe("0");
    expect(remove.getAttribute("role")).toBe("button");
    remove.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));

    expect(events).toEqual([{ pointer: "/tags", value: ["two"] }]);
  });

  it("shows the discriminated union's chosen branch and switches it when a new option is picked", async () => {
    const element = await mountObjectForm();

    // starts on branch "a" (SourceA): its api_key field is present
    expect(fieldAt(element, "/source/api_key")).not.toBeNull();

    const events: unknown[] = [];
    element.addEventListener("field-change", (event) => events.push((event as CustomEvent).detail));
    const picker = select(element, "/source");
    picker.value = "b";
    picker.dispatchEvent(new Event("change", { bubbles: true }));

    expect(events).toEqual([{ pointer: "/source", value: { type: "b", nested: null } }]);
  });

  it("does not show the discriminator field a second time inside the chosen branch", async () => {
    const element = await mountObjectForm();

    // the union's own picker already shows/controls "type" - the branch does not repeat it
    expect(fieldAt(element, "/source/type")).toBeNull();
    // a plain (non-discriminated) field with the same name elsewhere is unaffected
    expect(fieldAt(element, "/type")).not.toBeNull();
  });

  it("an object-level cycle (SourceB.nested pointing at SourceB) renders as a label plus a fake Add accordion item, like an empty list", async () => {
    const element = await mountObjectForm({ value: { ...value, source: { type: "b", nested: null } } });

    const nestedField = fieldAt(element, "/source/nested")!;
    expect(nestedField.querySelector("wa-button")).toBeNull();
    expect(nestedField.shadowRoot!.querySelector(".wa-form-control-label")?.textContent).toBe("SourceB");
    const addItem = nestedField.querySelector("wa-accordion-item")!;
    expect(addItem.getAttribute("label")).toBe("Add");
    expect(addItem.querySelector('[slot="icon"]')?.getAttribute("name")).toBe("plus");
    // one level only - no grand-nested object rendered until that item's add is triggered
    expect(fieldAt(element, "/source/nested/type")).toBeNull();
  });

  it("triggering the cycle's Add item seeds exactly one more level, itself bottoming out again", async () => {
    const element = await mountObjectForm({ value: { ...value, source: { type: "b", nested: null } } });
    const events: unknown[] = [];
    element.addEventListener("field-change", (event) => events.push((event as CustomEvent).detail));

    const nestedField = fieldAt(element, "/source/nested")!;
    const accordion = nestedField.querySelector("wa-accordion")!;
    const addItem = nestedField.querySelector("wa-accordion-item")!;
    accordion.dispatchEvent(new CustomEvent("wa-expand", { detail: { item: addItem }, cancelable: true }));

    expect(events).toEqual([{ pointer: "/source/nested", value: { type: "b", nested: null } }]);
  });

  it("a bare oneOf with no discriminator renders an unlabeled branch picker built from each branch's type name", async () => {
    const element = await mountObjectForm();

    const options = fieldAt(element, "/formula")!.querySelectorAll("wa-option");
    expect(Array.from(options).map((o) => o.getAttribute("value"))).toEqual(["IndexFormula", "MinimumFormula"]);
  });

  it("guesses the bare oneOf's current branch from the value's own required keys", async () => {
    const element = await mountObjectForm({ value: { ...value, formula: { kind: "minimum", minimum: [] } } });

    const picker = select(element, "/formula");
    expect(picker.value).toBe("MinimumFormula");
    // and renders that branch's own fields
    expect(fieldAt(element, "/formula/minimum")).not.toBeNull();
  });

  it("a recursive array-of-union field (Formula.minimum: Formula[]) does not crash and starts empty", async () => {
    const element = await mountObjectForm({ value: { ...value, formula: { kind: "minimum", minimum: [] } } });

    expect(fieldAt(element, "/formula/minimum")!.querySelectorAll("cofy-any-form")).toHaveLength(0);
  });

  it("shows an issue against the exact field it belongs to", async () => {
    const issues: ValidationIssue[] = [{ pointer: "/source/api_key", message: "required", keyword: "required" }];
    const element = await mountObjectForm({ issues });

    const list = fieldAt(element, "/source/api_key")!.shadowRoot!.querySelector(".cofy-field-issues");
    expect(list?.textContent).toContain("required");
    expect(fieldAt(element, "/name")!.shadowRoot!.querySelector(".cofy-field-issues")).toBeNull();
  });

  it("shows a union's own failed-match issue at the union's pointer, not swallowed", async () => {
    const issues: ValidationIssue[] = [{ pointer: "/source", message: "does not match a branch", keyword: "oneOf" }];
    const element = await mountObjectForm({ issues });

    expect(fieldAt(element, "/source")!.shadowRoot!.textContent).toContain("does not match a branch");
  });

  it("hides a property named in hide, so a host rendering it itself does not get it twice", async () => {
    const element = await mountObjectForm();
    expect(fieldAt(element, "/type")).not.toBeNull();

    element.hide = ["type"];
    await element.updateComplete;

    expect(fieldAt(element, "/type")).toBeNull();
    // its sibling fields are unaffected
    expect(fieldAt(element, "/name")).not.toBeNull();
  });

  it("does not wrap the document root in a card, only nested objects", async () => {
    const element = await mountObjectForm();

    expect(element.shadowRoot!.querySelector("wa-card")).toBeNull();
  });

  it("shows the document root's own issue after its fields, matching where a leaf field shows its own", async () => {
    const issues: ValidationIssue[] = [{ pointer: "", message: "root problem", keyword: "custom" }];
    const element = await mountObjectForm({ issues });

    // the root wraps in cofy-field-shell too (just without a card, since it is not `wrapped`)
    const shell = element.shadowRoot!.querySelector("cofy-field-shell")!;
    const issuesList = shell.shadowRoot!.querySelector(".cofy-field-issues")!;
    expect(issuesList.textContent).toContain("root problem");
  });

  it("wraps a nested object in a headerless card, with its label above the card", async () => {
    const nestedSchema: JsonSchema = { title: "Nested Thing", type: "object", properties: { a: { type: "string" } } };
    const element = document.createElement("cofy-object-form");
    await provideI18n(element);
    element.schema = nestedSchema;
    element.root = nestedSchema;
    element.pointer = "/thing";
    element.value = { a: "x" };
    document.body.append(element);
    await element.updateComplete;

    const shell = element.shadowRoot!.querySelector("cofy-field-shell")!;
    const label = shell.shadowRoot!.querySelector(".wa-form-control-label");
    // the card is the caller's own markup, slotted into cofy-field-shell - a light-DOM child of
    // it, not inside its shadow root (unlike the label, which cofy-field-shell renders itself).
    const card = shell.querySelector("wa-card");
    expect(label?.textContent).toBe("Nested Thing");
    expect(card).not.toBeNull();
    expect(card!.querySelector('[slot="header"]')).toBeNull();
  });

  it("shows a nested object's own issue after its fields, not before, matching a leaf field's own", async () => {
    const nestedSchema: JsonSchema = { title: "Nested Thing", type: "object", properties: { a: { type: "string" } } };
    const element = document.createElement("cofy-object-form");
    await provideI18n(element);
    element.schema = nestedSchema;
    element.root = nestedSchema;
    element.pointer = "/thing";
    element.value = { a: "x" };
    element.issues = [{ pointer: "/thing", message: "bad thing", keyword: "custom" }];
    document.body.append(element);
    await element.updateComplete;

    const shell = element.shadowRoot!.querySelector("cofy-field-shell")!;
    const issuesList = shell.shadowRoot!.querySelector(".cofy-field-issues")!;
    expect(issuesList.textContent).toContain("bad thing");
    // cofy-field-shell's own test already verifies it puts issues after the slot generically
  });

  it("renders a bare object with no card and no label of its own", async () => {
    const nestedSchema: JsonSchema = { title: "Nested Thing", type: "object", properties: { a: { type: "string" } } };
    const element = document.createElement("cofy-object-form");
    await provideI18n(element);
    element.schema = nestedSchema;
    element.root = nestedSchema;
    element.pointer = "/thing";
    element.value = { a: "x" };
    element.bare = true;
    document.body.append(element);
    await element.updateComplete;

    const shell = element.shadowRoot!.querySelector("cofy-field-shell")!;
    expect(shell.querySelector("wa-card")).toBeNull();
    expect(shell.shadowRoot!.querySelector(".wa-form-control-label")).toBeNull();
  });

  it("wraps a list in an accordion, with its label above (not a card - the accordion is its own boundary)", async () => {
    const listSchema: JsonSchema = { title: "Tags", type: "array", items: { type: "string" } };
    const element = document.createElement("cofy-list-form");
    await provideI18n(element);
    element.schema = listSchema;
    element.root = listSchema;
    element.pointer = "/tags";
    element.value = ["a"];
    document.body.append(element);
    await element.updateComplete;

    const shell = element.shadowRoot!.querySelector("cofy-field-shell")!;
    expect(shell.shadowRoot!.querySelector(".wa-form-control-label")?.textContent).toBe("Tags");
    expect(shell.querySelector("wa-accordion")).not.toBeNull();
    expect(shell.querySelector("wa-card")).toBeNull();
  });

  it("appends a trailing 'Add' accordion item with a plus icon in place of the expand chevron", async () => {
    const element = await mountObjectForm();

    const addItem = fieldAt(element, "/tags")!.querySelector(".cofy-list-add")!;
    expect(addItem).not.toBeNull();
    expect(addItem.getAttribute("label")).toBe("Add");
    expect(addItem.querySelector('[slot="icon"]')?.getAttribute("name")).toBe("plus");
  });

  it("collapses each list item by default, showing only its position and a delete action", async () => {
    const element = await mountObjectForm();

    const items = fieldAt(element, "/tags")!.querySelectorAll<HTMLElement & { expanded: boolean }>(
      "wa-accordion-item:not(.cofy-list-add)",
    );
    expect(items).toHaveLength(2);
    expect(Array.from(items).every((item) => !item.expanded)).toBe(true);
    expect(items[0]!.querySelector('[slot="label"]')?.textContent).toContain("1");
    expect(items[1]!.querySelector('[slot="label"]')?.textContent).toContain("2");
  });

  it("renders an object list item bare - the accordion item is already its boundary", async () => {
    const itemSchema: JsonSchema = { title: "Row", type: "object", properties: { a: { type: "string" } } };
    const listSchema: JsonSchema = { title: "Rows", type: "array", items: itemSchema };
    const element = document.createElement("cofy-list-form");
    await provideI18n(element);
    element.schema = listSchema;
    element.root = listSchema;
    element.pointer = "/rows";
    element.value = [{ a: "x" }];
    document.body.append(element);
    await element.updateComplete;
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(element.shadowRoot!.querySelector("wa-card")).toBeNull();
  });

  it("opens a newly added item automatically, without needing another click", async () => {
    const listSchema: JsonSchema = { title: "Tags", type: "array", items: { type: "string" } };
    const element = document.createElement("cofy-list-form");
    await provideI18n(element);
    element.schema = listSchema;
    element.root = listSchema;
    element.pointer = "/tags";
    element.value = ["one"];
    document.body.append(element);
    await element.updateComplete;
    await new Promise((resolve) => setTimeout(resolve, 0));

    let emitted: unknown;
    element.addEventListener("field-change", (event) => {
      emitted = (event as CustomEvent<{ value: unknown }>).detail.value;
    });
    const accordion = element.shadowRoot!.querySelector("wa-accordion")!;
    accordion.dispatchEvent(
      new CustomEvent("wa-expand", { detail: { item: accordion.querySelector(".cofy-list-add") }, cancelable: true }),
    );

    // Echo the new value straight back down, exactly as a real host's onFormChange would.
    element.value = emitted;
    await element.updateComplete;
    await new Promise((resolve) => setTimeout(resolve, 0));

    const newItem = element.shadowRoot!.querySelectorAll<HTMLElement & { expanded: boolean }>(
      "wa-accordion-item:not(.cofy-list-add)",
    )[1]!;
    expect(newItem.expanded).toBe(true);
  });

  it("keeps a manually opened item open across a later, unrelated re-render", async () => {
    const listSchema: JsonSchema = { title: "Tags", type: "array", items: { type: "string" } };
    const element = document.createElement("cofy-list-form");
    await provideI18n(element);
    element.schema = listSchema;
    element.root = listSchema;
    element.pointer = "/tags";
    element.value = ["one", "two"];
    document.body.append(element);
    await element.updateComplete;
    await new Promise((resolve) => setTimeout(resolve, 0));

    const accordion = element.shadowRoot!.querySelector("wa-accordion")!;
    const items = element.shadowRoot!.querySelectorAll<HTMLElement & { expanded: boolean }>(
      "wa-accordion-item:not(.cofy-list-add)",
    );
    accordion.dispatchEvent(new CustomEvent("wa-expand", { detail: { item: items[0] }, cancelable: true }));
    await element.updateComplete;
    expect(items[0]!.expanded).toBe(true);

    // Something elsewhere in the form changed - a new issues array is exactly what a real host
    // passes down after every keystroke, whether or not it touches this list at all.
    element.issues = [{ pointer: "/somewhere/else", message: "unrelated", keyword: "custom" }];
    await element.updateComplete;

    expect(items[0]!.expanded).toBe(true);
  });

  it("shows a list's own issue after the accordion, matching where a leaf field shows its own", async () => {
    const issues: ValidationIssue[] = [{ pointer: "/tags", message: "too many", keyword: "maxItems" }];
    const element = await mountObjectForm({ issues });

    const field = fieldAt(element, "/tags")!;
    expect(field.querySelector("wa-accordion")).not.toBeNull();
    const issuesList = field.shadowRoot!.querySelector(".cofy-field-issues")!;
    expect(issuesList.textContent).toContain("too many");
  });

  it("groups a union in its own headerless card, with the type select inside it", async () => {
    const element = await mountObjectForm();

    const shell = fieldAt(element, "/source")!;
    // the card is the union's own markup, slotted into cofy-field-shell - a light-DOM child of
    // it, not inside its shadow root.
    const card = shell.querySelector("wa-card")!;
    expect(card).not.toBeNull();
    expect(card.querySelector('[slot="header"]')).toBeNull();
    expect(card.querySelector("wa-select")).not.toBeNull();
  });

  it("renders the union's chosen object branch without its own card - the union's card is its boundary", async () => {
    const element = await mountObjectForm();

    // /source resolves to SourceA, an object - the whole subtree must have exactly one wa-card
    // (the union's own), not a second one from the branch.
    expect(deepQueryAll(fieldAt(element, "/source")!, "wa-card")).toHaveLength(1);
  });

  it("labels the union's own picker generically ('Type'), since the field's own label is now above the card", async () => {
    const element = await mountObjectForm();

    const picker = select(element, "/source");
    expect(picker.getAttribute("label")).toBe("Type");
  });

  it("shows a union's own issue after its picker/branch, not before, matching a leaf field's own", async () => {
    const issues: ValidationIssue[] = [{ pointer: "/source", message: "does not match a branch", keyword: "oneOf" }];
    const element = await mountObjectForm({ issues });

    const cardField = fieldAt(element, "/source")!;
    const slot = cardField.shadowRoot!.querySelector("slot")!;
    const issuesList = cardField.shadowRoot!.querySelector(".cofy-field-issues")!;
    expect(issuesList.textContent).toContain("does not match a branch");
    expect(slot.compareDocumentPosition(issuesList)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
  });

  it("renders an Optional[array-of-union] item through the real union picker, not as raw unknown JSON", async () => {
    // The shape of a tariff module's `formats: list[Format] | None` - the array only shows up
    // once the surrounding anyOf/null wrapper is unwrapped, and each item is itself a
    // discriminated union. A child mounted with the wrong (still-wrapped) schema would see no
    // `items` at all and fall back to cofy-unknown-form for every element.
    const parentSchema: JsonSchema = {
      type: "object",
      properties: {
        formats: {
          anyOf: [
            {
              type: "array",
              items: {
                discriminator: { propertyName: "type", mapping: { csv: "#/$defs/Csv", json: "#/$defs/Json" } },
                oneOf: [{ $ref: "#/$defs/Csv" }, { $ref: "#/$defs/Json" }],
              },
            },
            { type: "null" },
          ],
          default: null,
          title: "Formats",
        },
      },
      $defs: {
        Csv: {
          title: "Csv",
          type: "object",
          properties: { type: { const: "csv", default: "csv", type: "string" } },
          required: ["type"],
        },
        Json: {
          title: "Json",
          type: "object",
          properties: { type: { const: "json", default: "json", type: "string" } },
          required: ["type"],
        },
      },
    };
    const element = document.createElement("cofy-object-form");
    await provideI18n(element);
    element.schema = parentSchema;
    element.root = parentSchema;
    element.pointer = "";
    element.value = { formats: [{ type: "csv" }] };
    document.body.append(element);
    await element.updateComplete;
    await new Promise((resolve) => setTimeout(resolve, 0));

    const item = fieldAt(element, "/formats/0")!;
    expect(item.querySelector("cofy-yaml-editor")).toBeNull();
    expect(item.querySelector("wa-select")).not.toBeNull();
  });

  it("renders a dict-shaped object (additionalProperties, no fixed properties) as a YAML editor, not an empty card", async () => {
    // The shape of energy_cost's TariffVersion.injection/consumption/fixed/capacity -
    // `dict[str, Formula]`, no `properties` key at all for cofy-object-form to draw a field for.
    const parentSchema: JsonSchema = {
      type: "object",
      properties: {
        injection: {
          type: "object",
          additionalProperties: { oneOf: [{ type: "string" }] },
          title: "Injection",
        },
      },
    };
    const element = document.createElement("cofy-object-form");
    await provideI18n(element);
    element.schema = parentSchema;
    element.root = parentSchema;
    element.pointer = "";
    element.value = { injection: { peak: "flat" } };
    document.body.append(element);
    await element.updateComplete;
    await new Promise((resolve) => setTimeout(resolve, 0));

    const field = fieldAt(element, "/injection")!;
    expect(field.querySelector("wa-button")).toBeNull();
    expect(field.querySelector("cofy-yaml-editor")).not.toBeNull();
    expect(field.shadowRoot!.querySelector(".wa-form-control-label")?.textContent).toBe("Injection");
  });
});

describe("cofy-unknown-form", () => {
  const unknownSchema: JsonSchema = { title: "Extra Config" };

  it("shows the value as a YAML editor, labelled with the field's own title", async () => {
    const element = document.createElement("cofy-unknown-form");
    await provideI18n(element);
    element.schema = unknownSchema;
    element.root = unknownSchema;
    element.pointer = "/extra";
    element.value = { a: 1, b: "two" };
    document.body.append(element);
    await element.updateComplete;

    const shell = element.shadowRoot!.querySelector("cofy-field-shell")!;
    expect(shell.shadowRoot!.querySelector(".wa-form-control-label")?.textContent).toBe("Extra Config");
    const editor = element.shadowRoot!.querySelector("cofy-yaml-editor") as HTMLElement & { text: string };
    expect(editor).not.toBeNull();
    expect(editor.text).toContain("a: 1");
    expect(editor.text).toContain("b: two");
  });

  it("dispatches field-change with the parsed value once the YAML is edited", async () => {
    const element = document.createElement("cofy-unknown-form");
    await provideI18n(element);
    element.schema = unknownSchema;
    element.root = unknownSchema;
    element.pointer = "/extra";
    element.value = { a: 1 };
    document.body.append(element);
    await element.updateComplete;

    const events: unknown[] = [];
    element.addEventListener("field-change", (event) => events.push((event as CustomEvent).detail));

    const editor = element.shadowRoot!.querySelector("cofy-yaml-editor")!;
    editor.dispatchEvent(
      new CustomEvent("yaml-change", { detail: { text: "a: 2\n", value: { a: 2 }, syntaxErrors: [] } }),
    );

    expect(events).toEqual([{ pointer: "/extra", value: { a: 2 } }]);
  });

  it("does not dispatch field-change while the YAML has syntax errors, and shows them instead", async () => {
    const element = document.createElement("cofy-unknown-form");
    await provideI18n(element);
    element.schema = unknownSchema;
    element.root = unknownSchema;
    element.pointer = "/extra";
    element.value = { a: 1 };
    document.body.append(element);
    await element.updateComplete;

    const events: unknown[] = [];
    element.addEventListener("field-change", (event) => events.push((event as CustomEvent).detail));

    const editor = element.shadowRoot!.querySelector("cofy-yaml-editor")!;
    editor.dispatchEvent(
      new CustomEvent("yaml-change", { detail: { text: "a: [", value: undefined, syntaxErrors: ["bad"] } }),
    );
    await element.updateComplete;

    expect(events).toEqual([]);
    const shell = element.shadowRoot!.querySelector("cofy-field-shell")!;
    expect(shell.shadowRoot!.querySelector(".cofy-field-issues")?.textContent).toContain("bad");
  });
});

describe("cofy-field-shell", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  async function mountFieldShell(
    options: { label?: string; issues?: ValidationIssue[] } = {},
  ): Promise<HTMLElement> {
    const element = document.createElement("cofy-field-shell");
    await provideI18n(element);
    element.label = options.label ?? "";
    element.issues = options.issues ?? [];
    element.innerHTML = "<span>a control</span>";
    document.body.append(element);
    await element.updateComplete;
    return element;
  }

  it("renders its slotted control", async () => {
    const element = await mountFieldShell();

    expect(element.textContent).toContain("a control");
  });

  it("shows no label when it is empty", async () => {
    const element = await mountFieldShell();

    expect(element.shadowRoot!.querySelector(".wa-form-control-label")).toBeNull();
  });

  it("shows its own label above the slotted control", async () => {
    const element = await mountFieldShell({ label: "Source" });

    const label = element.shadowRoot!.querySelector(".wa-form-control-label");
    const slot = element.shadowRoot!.querySelector("slot")!;
    expect(label?.textContent).toBe("Source");
    expect(label?.compareDocumentPosition(slot)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
  });

  it("shows no issues list when there are none", async () => {
    const element = await mountFieldShell();

    expect(element.shadowRoot!.querySelector(".cofy-field-issues")).toBeNull();
  });

  it("shows its own issues below the slotted control", async () => {
    const element = await mountFieldShell({ issues: [{ pointer: "/x", message: "bad value", keyword: "custom" }] });

    const slot = element.shadowRoot!.querySelector("slot")!;
    const issuesList = element.shadowRoot!.querySelector(".cofy-field-issues")!;
    expect(issuesList.textContent).toContain("bad value");
    expect(slot.compareDocumentPosition(issuesList)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
  });
});

const catalog: AllowedModule[] = [{ type: "demo", description: "A demo module", schema }];

async function mountModuleForm(
  moduleValue: unknown,
  options: { catalog?: AllowedModule[]; locked?: boolean } = {},
): Promise<CofyModuleForm> {
  const element = document.createElement("cofy-module-form");
  await provideI18n(element);
  element.catalog = options.catalog ?? catalog;
  element.value = moduleValue;
  element.issues = [];
  element.locked = options.locked ?? false;
  document.body.append(element);
  await element.updateComplete;
  await new Promise((resolve) => setTimeout(resolve, 0));
  return element;
}

describe("cofy-module-form", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("renders the generated form by default when the type's schema is known", async () => {
    const element = await mountModuleForm(value);

    expect(element.shadowRoot!.querySelector("cofy-object-form")).not.toBeNull();
    expect(element.shadowRoot!.querySelector("cofy-yaml-editor")).toBeNull();
  });

  it("renders the module's own type as a select, integrated into the same form", async () => {
    const element = await mountModuleForm(value);

    const select = element.shadowRoot!.querySelector<HTMLElement & { value: string }>("wa-select")!;
    expect(select.value).toBe("demo");
    const options = element.shadowRoot!.querySelectorAll("wa-option");
    expect(Array.from(options).map((o) => o.getAttribute("value"))).toEqual(["demo"]);
  });

  it("disables the type select once the module already exists", async () => {
    const element = await mountModuleForm(value, { locked: true });

    const select = element.shadowRoot!.querySelector<HTMLElement>("wa-select")!;
    expect(select.hasAttribute("disabled")).toBe(true);
  });

  it("leaves the type select enabled while creating", async () => {
    const element = await mountModuleForm(null);

    const select = element.shadowRoot!.querySelector<HTMLElement>("wa-select")!;
    expect(select.hasAttribute("disabled")).toBe(false);
  });

  it("shows nothing below the picker until a type is chosen", async () => {
    const element = await mountModuleForm(null);

    expect(element.shadowRoot!.querySelector("cofy-object-form")).toBeNull();
    expect(element.shadowRoot!.querySelector("cofy-yaml-editor")).toBeNull();
  });

  it("picking a type seeds a fresh document and emits it", async () => {
    const element = await mountModuleForm(null);
    const events: unknown[] = [];
    element.addEventListener("module-form-change", (event) => events.push((event as CustomEvent).detail));

    const select = element.shadowRoot!.querySelector<HTMLElement & { value: string }>("wa-select")!;
    select.value = "demo";
    select.dispatchEvent(new Event("change", { bubbles: true }));

    expect(events).toHaveLength(1);
    const seeded = (events[0] as { value: Record<string, unknown> }).value;
    expect(seeded["type"]).toBe("demo");
    expect(seeded["name"]).toBe("");
  });

  it("does not render the type field a second time inside the form itself", async () => {
    const element = await mountModuleForm(value);

    expect(fieldAt(element.shadowRoot!.querySelector("cofy-object-form")!, "/type")).toBeNull();
  });

  it("shows the type picker's own issue through cofy-field-shell", async () => {
    const issues: ValidationIssue[] = [{ pointer: "/type", message: "unknown type", keyword: "custom" }];
    const element = await mountModuleForm(null, { catalog: [] });
    element.issues = issues;
    await element.updateComplete;

    const shell = element.shadowRoot!.querySelector("cofy-field-shell")!;
    expect(shell.querySelector("wa-select")).not.toBeNull();
    expect(shell.shadowRoot!.querySelector(".cofy-field-issues")?.textContent).toContain("unknown type");
  });

  it("shows a YAML syntax error through cofy-field-shell, wrapping the editor", async () => {
    const element = await mountModuleForm({ type: "unknown", name: "x" }, { locked: true });

    const editor = element.shadowRoot!.querySelector("cofy-yaml-editor")!;
    editor.dispatchEvent(
      new CustomEvent("yaml-change", { detail: { text: "a: [", value: undefined, syntaxErrors: ["bad yaml"] } }),
    );
    await element.updateComplete;

    const shell = element.shadowRoot!.querySelector("cofy-field-shell")!;
    expect(shell.querySelector("cofy-yaml-editor")).not.toBeNull();
    expect(shell.shadowRoot!.querySelector(".cofy-field-issues")?.textContent).toContain("bad yaml");
  });

  it("mode is host-controlled: setting the mode property switches views", async () => {
    const element = await mountModuleForm(value);
    expect(element.shadowRoot!.querySelector("cofy-object-form")).not.toBeNull();

    element.mode = "yaml";
    await element.updateComplete;
    expect(element.shadowRoot!.querySelector("cofy-yaml-editor")).not.toBeNull();
    expect(element.shadowRoot!.querySelector("cofy-object-form")).toBeNull();

    element.mode = "form";
    await element.updateComplete;
    expect(element.shadowRoot!.querySelector("cofy-object-form")).not.toBeNull();
  });

  it("hides the type picker once in YAML mode - it is already part of that text", async () => {
    const element = await mountModuleForm(value);
    expect(element.shadowRoot!.querySelector("wa-select")).not.toBeNull();

    element.mode = "yaml";
    await element.updateComplete;

    expect(element.shadowRoot!.querySelector("wa-select")).toBeNull();
  });

  it("switching to YAML reflects a form edit made just before, without an explicit save", async () => {
    const element = await mountModuleForm(value);
    let emitted: unknown;
    element.addEventListener("module-form-change", (event) => {
      emitted = (event as CustomEvent<{ value: unknown }>).detail.value;
    });

    const input = fieldAt(element.shadowRoot!.querySelector("cofy-object-form")!, "/name")!.querySelector<
      HTMLElement & { value: string }
    >("wa-input")!;
    input.value = "renamed";
    input.dispatchEvent(new Event("input", { bubbles: true, composed: true }));

    // Echo the edit straight back down, exactly as a real host's onFormChange would - the same
    // reference emit() just produced, so willUpdate's own-echo guard skips the ordinary resync
    // and only the "entering yaml" path is what is actually under test here.
    element.value = emitted;
    await element.updateComplete;

    element.mode = "yaml";
    await element.updateComplete;

    expect(element.shadowRoot!.querySelector("cofy-yaml-editor")!.text).toContain("name: renamed");
  });

  it("switching back to form reflects a YAML edit made just before", async () => {
    const element = await mountModuleForm(value);
    element.mode = "yaml";
    await element.updateComplete;
    let emitted: unknown;
    element.addEventListener("module-form-change", (event) => {
      emitted = (event as CustomEvent<{ value: unknown }>).detail.value;
    });

    element.shadowRoot!.querySelector("cofy-yaml-editor")!.dispatchEvent(
      new CustomEvent("yaml-change", {
        detail: { text: "type: demo\nname: renamed\n", value: { type: "demo", name: "renamed" }, syntaxErrors: [] },
      }),
    );
    element.value = emitted;
    await element.updateComplete;

    element.mode = "form";
    await element.updateComplete;
    // switching back to form mounts a brand new cofy-object-form, which needs its own tick.
    await new Promise((resolve) => setTimeout(resolve, 0));

    const input = fieldAt(element.shadowRoot!.querySelector("cofy-object-form")!, "/name")!.querySelector<
      HTMLElement & { value: string }
    >("wa-input")!;
    expect(input.value).toBe("renamed");
  });

  it("forces YAML mode and hides the picker once a type is set that is not in the catalog", async () => {
    const element = await mountModuleForm({ type: "unknown", name: "x" }, { locked: true });

    expect(element.shadowRoot!.querySelector("wa-select")).toBeNull();
    expect(element.shadowRoot!.querySelector("cofy-yaml-editor")).not.toBeNull();
  });

  it("reports a form edit as one module-form-change with the whole new value", async () => {
    const element = await mountModuleForm(value);
    const events: unknown[] = [];
    element.addEventListener("module-form-change", (event) => events.push((event as CustomEvent).detail));

    const input = fieldAt(element.shadowRoot!.querySelector("cofy-object-form")!, "/name")!.querySelector<
      HTMLElement & { value: string }
    >("wa-input")!;
    input.value = "renamed";
    input.dispatchEvent(new Event("input", { bubbles: true, composed: true }));

    expect(events).toEqual([{ value: { ...value, name: "renamed" } }]);
  });
});
