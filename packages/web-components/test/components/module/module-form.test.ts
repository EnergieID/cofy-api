import { beforeEach, describe, expect, it } from "vitest";
import type { JsonSchema } from "@cofy/frontend-sdk";

import "../../../src/components/module/cofy-module-form.js";
import type { CofyModuleForm } from "../../../src/components/module/cofy-module-form.js";

/** A module type that is self-referential at its own schema root - `model_json_schema()`
 * emits this exact shape (`$defs` plus a top-level `$ref`) for a recursive pydantic model,
 * unlike every other catalog entry which has `properties` directly at the top level. */
const recursiveSchema: JsonSchema = {
  $ref: "#/$defs/Directive",
  $defs: {
    Directive: {
      type: "object",
      title: "Directive",
      properties: {
        type: { const: "directive", default: "directive" },
        name: { type: "string" },
      },
      required: ["name"],
    },
  },
};

const catalog = [{ type: "directive", description: "Directive module", schema: recursiveSchema }];

/** Every field in the family lives in its own shadow root a few levels below the one that
 * mounted it, so a plain `querySelector` from the top cannot see it - this walks light-DOM
 * descendants at each level and follows any shadow root it finds. */
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

async function mountModuleForm(value: unknown): Promise<CofyModuleForm> {
  const element = document.createElement("cofy-module-form");
  element.catalog = catalog;
  element.value = value;
  document.body.append(element);
  await element.updateComplete;
  await new Promise((resolve) => setTimeout(resolve, 0));
  return element;
}

describe("cofy-module-form with a self-referential top-level schema", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("still shows the type's own fields, instead of a blank form", async () => {
    const element = await mountModuleForm({ type: "directive", name: "spot" });

    const objectForm = element.shadowRoot!.querySelector("cofy-object-form");
    expect(objectForm).not.toBeNull();

    const field = deepQuery(objectForm!.shadowRoot!, '[data-pointer="/name"]');
    const input = field?.querySelector<HTMLElement & { value: string }>("wa-input") ?? null;

    expect(input).not.toBeNull();
    expect(input!.value).toBe("spot");
  });
});
