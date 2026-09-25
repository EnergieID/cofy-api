import { beforeEach, describe, expect, it } from "vitest";
import { ContextProvider } from "@lit/context";
import type { JsonSchema } from "@cofy/frontend-sdk";

import "../../../src/components/form/cofy-union-form.js";
import { i18nContext } from "../../../src/context.js";
import type { CofyUnionForm } from "../../../src/components/form/cofy-union-form.js";
import { testI18n } from "../../support/i18n.js";

/** A bare, non-discriminated union whose branches are inline and untitled - like the
 * `Union[int, str]` a plain pydantic annotation (with no `Field(discriminator=...)`) produces. */
const schema: JsonSchema = { oneOf: [{ type: "integer" }, { type: "string" }] };

async function mountUnionForm(value: unknown): Promise<CofyUnionForm> {
  const element = document.createElement("cofy-union-form");
  new ContextProvider(element, { context: i18nContext, initialValue: await testI18n() });
  element.schema = schema;
  element.root = schema;
  element.pointer = "/value";
  element.value = value;
  document.body.append(element);
  await element.updateComplete;
  return element;
}

describe("cofy-union-form with untitled, non-discriminated branches", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("gives every option a unique, non-empty value instead of collapsing them onto \"\"", async () => {
    const element = await mountUnionForm(0);

    const options = element.shadowRoot!.querySelectorAll("wa-option");
    const values = Array.from(options).map((option) => option.getAttribute("value"));

    expect(new Set(values).size).toBe(values.length);
    expect(values.every((value) => value !== "")).toBe(true);
  });

  it("actually switches branch when a different option is picked, instead of silently no-opping", async () => {
    const element = await mountUnionForm(0);
    const events: unknown[] = [];
    element.addEventListener("field-change", (event) => events.push((event as CustomEvent).detail));

    const picker = element.shadowRoot!.querySelector<HTMLElement & { value: string }>("wa-select")!;
    const options = element.shadowRoot!.querySelectorAll("wa-option");
    // The second option is the untitled "string" branch - its value only exists because of the
    // index fallback, not a name, since it has none.
    picker.value = options[1]!.getAttribute("value")!;
    picker.dispatchEvent(new Event("change", { bubbles: true }));

    expect(events).toEqual([{ pointer: "/value", value: "" }]);
  });
});
