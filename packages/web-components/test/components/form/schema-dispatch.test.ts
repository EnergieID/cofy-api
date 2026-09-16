import { describe, expect, it } from "vitest";
import type { JsonSchema } from "@cofy/frontend-sdk";

import { resolveFieldKind } from "../../../src/components/form/schema-dispatch.js";

describe("resolveFieldKind", () => {
  it("resolves a plain string", () => {
    expect(resolveFieldKind({ type: "string" }, {})).toEqual({ kind: "string" });
  });

  it("resolves a plain number and integer alike", () => {
    expect(resolveFieldKind({ type: "number" }, {})).toEqual({ kind: "number" });
    expect(resolveFieldKind({ type: "integer" }, {})).toEqual({ kind: "number" });
  });

  it("resolves a boolean", () => {
    expect(resolveFieldKind({ type: "boolean" }, {})).toEqual({ kind: "boolean" });
  });

  it("resolves a const-only discriminator field, like `type`", () => {
    const schema = { const: "billing", default: "billing", type: "string" };
    expect(resolveFieldKind(schema, {})).toEqual({ kind: "const", value: "billing" });
  });

  it("resolves a password/writeOnly string as a secret, not a plain string", () => {
    const schema = { type: "string", format: "password", writeOnly: true };
    expect(resolveFieldKind(schema, {})).toEqual({ kind: "secret" });
  });

  it("resolves an object with properties", () => {
    const schema = { type: "object", properties: { name: { type: "string" } } };
    expect(resolveFieldKind(schema, {})).toEqual({ kind: "object", schema });
  });

  it("treats a dict-shaped object (additionalProperties, no fixed properties) as unknown", () => {
    // `dict[str, Formula]` - no `properties` key for the object renderer to draw a field for.
    const schema = { type: "object", additionalProperties: { oneOf: [{ type: "string" }] } };
    expect(resolveFieldKind(schema, {})).toEqual({ kind: "unknown", schema });
  });

  it("resolves an array, carrying its items schema", () => {
    const schema = { type: "array", items: { type: "string" } };
    expect(resolveFieldKind(schema, {})).toEqual({ kind: "array", schema, items: { type: "string" } });
  });

  it("treats a missing/unrecognized type as unknown, not a crash", () => {
    expect(resolveFieldKind({}, {})).toEqual({ kind: "unknown", schema: {} });
  });

  it("resolves a local $ref before deciding the kind", () => {
    const costGroup = { enum: ["low", "high"] };
    const root: JsonSchema = { $defs: { CostGroup: costGroup } };
    const schema = { $ref: "#/$defs/CostGroup" };

    expect(resolveFieldKind(schema, root)).toEqual({ kind: "enum", schema: costGroup, values: ["low", "high"] });
  });

  it("resolves a discriminated oneOf union, carrying the discriminator mapping", () => {
    const schema: JsonSchema = {
      discriminator: { propertyName: "type", mapping: { directive: "#/$defs/DirectiveSourceSettings" } },
      oneOf: [{ $ref: "#/$defs/DirectiveSourceSettings" }],
    };

    const result = resolveFieldKind(schema, {});

    expect(result).toEqual({
      kind: "union",
      schema,
      branches: [{ $ref: "#/$defs/DirectiveSourceSettings" }],
      discriminator: { propertyName: "type", mapping: { directive: "#/$defs/DirectiveSourceSettings" } },
    });
  });

  it("resolves a bare oneOf with no discriminator key as a union with none", () => {
    // The energy_cost `Formula` shape: a callable/`kind`-tagged discriminator pydantic can't
    // express as `discriminator.mapping`.
    const schema: JsonSchema = { oneOf: [{ $ref: "#/$defs/MinimumFormula" }, { $ref: "#/$defs/TieredFormula" }] };

    const result = resolveFieldKind(schema, {});

    if (result.kind !== "union") throw new Error("expected a union");
    expect(result.discriminator).toBeUndefined();
  });

  it("unwraps Optional[string] (anyOf with one non-null branch) straight through to string", () => {
    const schema = { anyOf: [{ type: "string" }, { type: "null" }], default: null };
    expect(resolveFieldKind(schema, {})).toEqual({ kind: "string" });
  });

  it("unwraps Optional[$ref] through to the ref's own kind", () => {
    const costGroup = { enum: ["low", "high"] };
    const root: JsonSchema = { $defs: { CostGroup: costGroup } };
    const schema = { anyOf: [{ $ref: "#/$defs/CostGroup" }, { type: "null" }], default: null };

    expect(resolveFieldKind(schema, root)).toEqual({ kind: "enum", schema: costGroup, values: ["low", "high"] });
  });

  it("treats Optional[array-of-union] as an array, not a union - the null sits beside the array", () => {
    const schema = {
      anyOf: [
        {
          type: "array",
          items: { oneOf: [{ $ref: "#/$defs/JSONFormatSettings" }, { $ref: "#/$defs/CSVFormatSettings" }] },
        },
        { type: "null" },
      ],
      default: null,
    };

    const result = resolveFieldKind(schema, {});

    expect(result.kind).toBe("array");
  });

  it("treats a multi-branch anyOf with no null option as a union", () => {
    const schema = { anyOf: [{ type: "string" }, { type: "integer" }] };
    const result = resolveFieldKind(schema, {});

    if (result.kind !== "union") throw new Error("expected a union");
    expect(result.branches).toHaveLength(2);
  });
});
