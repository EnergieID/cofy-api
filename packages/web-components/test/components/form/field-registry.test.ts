import { describe, expect, it } from "vitest";
import type { JsonSchema } from "@cofy/frontend-sdk";

import { defaultFieldRegistry, FieldRegistry, type AS_YAML_OPTION } from "../../../src/components/form/field-registry.js";
import { resolveNode } from "../../../src/components/form/schema/resolve.js";

/** Dispatches *schema* through *registry*, the same way `cofy-any-form` does - the mounted tag always gets the resolved node. */
function dispatch(
  schema: JsonSchema,
  root: JsonSchema = {},
  registry = defaultFieldRegistry,
): { tag: string; schema: JsonSchema } | undefined {
  const node = resolveNode(schema, root);
  const match = registry.getFirstMatch(node, root);
  return match === undefined ? undefined : { tag: match.tag, schema: node };
}

describe("defaultFieldRegistry", () => {
  it("dispatches a plain string", () => {
    expect(dispatch({ type: "string" })).toEqual({ tag: "cofy-string-form", schema: { type: "string" } });
  });

  it("dispatches a number and integer alike", () => {
    expect(dispatch({ type: "number" })?.tag).toBe("cofy-number-form");
    expect(dispatch({ type: "integer" })?.tag).toBe("cofy-number-form");
  });

  it("dispatches a boolean", () => {
    expect(dispatch({ type: "boolean" })?.tag).toBe("cofy-boolean-form");
  });

  it("dispatches a const-only discriminator field, like `type`, ahead of the plain string it also is", () => {
    const schema = { const: "billing", default: "billing", type: "string" };
    expect(dispatch(schema)).toEqual({ tag: "cofy-const-form", schema });
  });

  it("dispatches a password/writeOnly string as a secret, ahead of the plain string it also is", () => {
    const schema = { type: "string", format: "password", writeOnly: true };
    expect(dispatch(schema)).toEqual({ tag: "cofy-secret-form", schema });
  });

  it("dispatches an object with properties, carrying the resolved node", () => {
    const schema = { type: "object", properties: { name: { type: "string" } } };
    expect(dispatch(schema)).toEqual({ tag: "cofy-object-form", schema });
  });

  it("dispatches a dict-shaped object (additionalProperties, no fixed properties), carrying the resolved node", () => {
    // `dict[str, Formula]` - no `properties` key for the object renderer to draw a field for.
    const schema = { type: "object", additionalProperties: { oneOf: [{ type: "string" }] } };
    expect(dispatch(schema)).toEqual({ tag: "cofy-dict-form", schema });
  });

  it("dispatches an array, carrying the resolved node", () => {
    const schema = { type: "array", items: { type: "string" } };
    expect(dispatch(schema)).toEqual({ tag: "cofy-list-form", schema });
  });

  it("leaves a missing/unrecognized type unmatched, not a crash", () => {
    expect(dispatch({})).toBeUndefined();
  });

  it("resolves a local $ref before dispatching", () => {
    const costGroup = { enum: ["low", "high"] };
    const root: JsonSchema = { $defs: { CostGroup: costGroup } };
    expect(dispatch({ $ref: "#/$defs/CostGroup" }, root)).toEqual({ tag: "cofy-enum-form", schema: costGroup });
  });

  it("dispatches a discriminated oneOf as a union", () => {
    const schema: JsonSchema = {
      discriminator: { propertyName: "type", mapping: { directive: "#/$defs/DirectiveSourceSettings" } },
      oneOf: [{ $ref: "#/$defs/DirectiveSourceSettings" }],
    };
    expect(dispatch(schema)).toEqual({ tag: "cofy-union-form", schema });
  });

  it("dispatches a bare oneOf with no discriminator key as a union too", () => {
    // The energy_cost `Formula` shape: a callable/`kind`-tagged discriminator pydantic can't
    // express as `discriminator.mapping`.
    const schema: JsonSchema = { oneOf: [{ $ref: "#/$defs/MinimumFormula" }, { $ref: "#/$defs/TieredFormula" }] };
    expect(dispatch(schema)?.tag).toBe("cofy-union-form");
  });

  it("unwraps Optional[string] (anyOf with one non-null branch) to dispatch as a string, carrying the resolved node", () => {
    const schema = { anyOf: [{ type: "string" }, { type: "null" }], default: null };
    expect(dispatch(schema)).toEqual({ tag: "cofy-string-form", schema: { type: "string" } });
  });

  it("unwraps Optional[$ref] through to the ref's own dispatch", () => {
    const costGroup = { enum: ["low", "high"] };
    const root: JsonSchema = { $defs: { CostGroup: costGroup } };
    const schema = { anyOf: [{ $ref: "#/$defs/CostGroup" }, { type: "null" }], default: null };
    expect(dispatch(schema, root)).toEqual({ tag: "cofy-enum-form", schema: costGroup });
  });

  it("treats Optional[array-of-union] as an array, not a union - the null sits beside the array", () => {
    const schema = {
      anyOf: [
        { type: "array", items: { oneOf: [{ $ref: "#/$defs/JSONFormatSettings" }, { $ref: "#/$defs/CSVFormatSettings" }] } },
        { type: "null" },
      ],
      default: null,
    };
    expect(dispatch(schema)?.tag).toBe("cofy-list-form");
  });

  it("treats a multi-branch anyOf with no null option as a union", () => {
    const schema = { anyOf: [{ type: "string" }, { type: "integer" }] };
    expect(dispatch(schema)?.tag).toBe("cofy-union-form");
  });
});

describe("FieldRegistry.getSummary", () => {
  it("summarizes a leaf by its own value", () => {
    expect(defaultFieldRegistry.getSummary({ type: "string" }, {}, "spot")).toBe("spot");
    expect(defaultFieldRegistry.getSummary({ type: "integer" }, {}, 3)).toBe("3");
    expect(defaultFieldRegistry.getSummary({ type: "boolean" }, {}, false)).toBe("false");
    expect(defaultFieldRegistry.getSummary({ enum: ["low", "high"] }, {}, "low")).toBe("low");
  });

  it("returns an empty string for a leaf with no value yet", () => {
    expect(defaultFieldRegistry.getSummary({ type: "string" }, {}, undefined)).toBe("");
  });

  it("never summarizes a secret, even though it is also a plain string", () => {
    const schema = { type: "string", format: "password", writeOnly: true };
    expect(defaultFieldRegistry.getSummary(schema, {}, "hunter2")).toBeUndefined();
  });

  it("summarizes an object by its own `type` value, title-cased, read directly rather than scanned from the schema's own const declarations", () => {
    const schema = { type: "object", properties: { type: { const: "csv" }, name: { type: "string" } } };
    expect(defaultFieldRegistry.getSummary(schema, {}, { type: "csv", name: "report.csv" })).toBe("Csv");
  });

  it("prefers `type` over `kind` when a value somehow has both", () => {
    const schema = { type: "object", properties: {} };
    expect(defaultFieldRegistry.getSummary(schema, {}, { type: "a", kind: "b" })).toBe("A");
  });

  it("falls back to `kind` when there is no `type`", () => {
    const schema = { type: "object", properties: {} };
    expect(defaultFieldRegistry.getSummary(schema, {}, { kind: "index" })).toBe("Index");
  });

  it("returns undefined for an object with neither tag", () => {
    const schema = { type: "object", properties: { name: { type: "string" } } };
    expect(defaultFieldRegistry.getSummary(schema, {}, { name: "spot" })).toBeUndefined();
  });

  it("summarizes a union the same way, since its value already carries whichever branch's tag is chosen", () => {
    const schema = { oneOf: [{ $ref: "#/$defs/A" }, { $ref: "#/$defs/B" }] };
    expect(defaultFieldRegistry.getSummary(schema, {}, { type: "b" })).toBe("B");
  });

  it("returns undefined for a union with nothing chosen yet", () => {
    const schema = { oneOf: [{ $ref: "#/$defs/A" }, { $ref: "#/$defs/B" }] };
    expect(defaultFieldRegistry.getSummary(schema, {}, null)).toBeUndefined();
  });

  it("returns undefined for a schema nothing matches", () => {
    expect(defaultFieldRegistry.getSummary({}, {}, "x")).toBeUndefined();
  });

  it("summarizes an array by its own length", () => {
    expect(defaultFieldRegistry.getSummary({ type: "array", items: { type: "string" } }, {}, ["a"])).toBe("1");
  });

  it("summarizes a dict by its own entry count", () => {
    const schema = { type: "object", additionalProperties: { type: "string" } };
    expect(defaultFieldRegistry.getSummary(schema, {}, { peak: "flat", off_peak: "flat" })).toBe("2");
  });
});

describe("FieldMapper.asYaml", () => {
  it("marks a plain array as optionally yaml, form by default", () => {
    const schema = { type: "array", items: { type: "string" } };
    expect(defaultFieldRegistry.getFirstMatch(resolveNode(schema, {}), {})?.asYaml).toBe("optional");
  });

  it("marks an array specifically titled Tariff as yaml by default", () => {
    const schema = { type: "array", items: { type: "string" }, title: "Tariff" };
    expect(defaultFieldRegistry.getFirstMatch(resolveNode(schema, {}), {})?.asYaml).toBe("default");
  });

  it("does not mark an array with an unrelated title as yaml by default", () => {
    const schema = { type: "array", items: { type: "string" }, title: "Tags" };
    expect(defaultFieldRegistry.getFirstMatch(resolveNode(schema, {}), {})?.asYaml).toBe("optional");
  });

  it("marks object, dict, and union as optionally yaml", () => {
    const asYaml = (schema: JsonSchema): AS_YAML_OPTION | undefined =>
      defaultFieldRegistry.getFirstMatch(resolveNode(schema, {}), {})?.asYaml;

    expect(asYaml({ type: "object", properties: { name: { type: "string" } } })).toBe("optional");
    expect(asYaml({ type: "object", additionalProperties: { type: "string" } })).toBe("optional");
    expect(asYaml({ oneOf: [{ $ref: "#/$defs/A" }, { $ref: "#/$defs/B" }] })).toBe("optional");
  });

  it("leaves plain leaves with no asYaml option at all", () => {
    expect(defaultFieldRegistry.getFirstMatch(resolveNode({ type: "string" }, {}), {})?.asYaml).toBeUndefined();
    expect(defaultFieldRegistry.getFirstMatch(resolveNode({ type: "boolean" }, {}), {})?.asYaml).toBeUndefined();
  });
});

describe("new FieldRegistry(overrides)", () => {
  it("tries the override before the built-ins", () => {
    const formula = { $ref: "#/$defs/Formula" };
    const registry = new FieldRegistry([{ tag: "cofy-formula-form", matches: (node): boolean => node === formula }]);

    // No $defs to resolve `formula` against, so the node handed to `matches` is `formula` itself.
    expect(dispatch(formula, {}, registry)?.tag).toBe("cofy-formula-form");
  });

  it("falls through to the built-ins for anything the override does not itself match", () => {
    const registry = new FieldRegistry([{ tag: "cofy-formula-form", matches: (): boolean => false }]);

    expect(dispatch({ type: "string" }, {}, registry)).toEqual({ tag: "cofy-string-form", schema: { type: "string" } });
  });

  it("registering nothing still dispatches through exactly the built-ins", () => {
    const registry = new FieldRegistry([]);

    expect(dispatch({ type: "string" }, {}, registry)?.tag).toBe("cofy-string-form");
    expect(dispatch({ type: "object", properties: {} }, {}, registry)?.tag).toBe("cofy-object-form");
  });
});
