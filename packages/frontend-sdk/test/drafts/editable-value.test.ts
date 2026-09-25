import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";

import { EditableValue } from "../../src/drafts/editable-value.js";
import { validate, type JsonSchema } from "../../src/validation.js";

const schemas = JSON.parse(
  readFileSync(new URL("../fixtures/schemas.json", import.meta.url), "utf8"),
) as Record<string, JsonSchema>;

describe("EditableValue", () => {
  it("starts clean and valid-looking", () => {
    const value = new EditableValue({ type: "tariff", name: "spot" });

    expect(value.issues).toEqual([]);
    expect(value.valid).toBe(true);
    expect(value.current).toEqual({ type: "tariff", name: "spot" });
  });

  it("replaces the current value wholesale on set", () => {
    const value = new EditableValue({ a: 1 });

    value.set({ a: 2 });

    expect(value.current).toEqual({ a: 2 });
  });

  it("records validation issues against a schema, matching the standalone validate()", () => {
    const value = new EditableValue({ type: "tariff", name: "spot", source: { type: "entsoe_day_ahead" } });

    const issues = value.check(schemas["tariff"]!);

    expect(issues.length).toBeGreaterThan(0);
    expect(value.valid).toBe(false);
    expect(issues).toEqual(validate(schemas["tariff"]!, value.current));
    expect(value.issues).toBe(issues);
  });
});
