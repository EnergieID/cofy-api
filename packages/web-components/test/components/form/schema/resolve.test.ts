import { describe, expect, it } from "vitest";
import type { JsonSchema } from "@cofy/frontend-sdk";

import {
  discriminatorOf,
  matchBranch,
  resolveNode,
  schemaTypeName,
  unionBranches,
} from "../../../../src/components/form/schema/resolve.js";

describe("resolveNode", () => {
  it("passes a plain leaf schema through unchanged", () => {
    const schema = { type: "string" };
    expect(resolveNode(schema, {})).toBe(schema);
  });

  it("resolves a local $ref", () => {
    const costGroup = { enum: ["low", "high"] };
    const root: JsonSchema = { $defs: { CostGroup: costGroup } };
    expect(resolveNode({ $ref: "#/$defs/CostGroup" }, root)).toBe(costGroup);
  });

  it("unwraps Optional[string] (anyOf with one non-null branch) straight through to string", () => {
    const schema = { anyOf: [{ type: "string" }, { type: "null" }], default: null };
    expect(resolveNode(schema, {})).toEqual({ type: "string" });
  });

  it("unwraps Optional[$ref] through to the ref's own target", () => {
    const costGroup = { enum: ["low", "high"] };
    const root: JsonSchema = { $defs: { CostGroup: costGroup } };
    const schema = { anyOf: [{ $ref: "#/$defs/CostGroup" }, { type: "null" }], default: null };
    expect(resolveNode(schema, root)).toBe(costGroup);
  });

  it("leaves a discriminated oneOf union alone - it is already terminal", () => {
    const schema: JsonSchema = { oneOf: [{ $ref: "#/$defs/DirectiveSourceSettings" }] };
    expect(resolveNode(schema, {})).toBe(schema);
  });

  it("leaves a multi-branch anyOf with no null option alone, as a union", () => {
    const schema = { anyOf: [{ type: "string" }, { type: "integer" }] };
    expect(resolveNode(schema, {})).toBe(schema);
  });

  it("treats Optional[array-of-union] as the array, not a union - the null sits beside the array", () => {
    const schema = {
      anyOf: [
        { type: "array", items: { oneOf: [{ $ref: "#/$defs/JSONFormatSettings" }, { $ref: "#/$defs/CSVFormatSettings" }] } },
        { type: "null" },
      ],
      default: null,
    };
    expect(resolveNode(schema, {})).toEqual(schema.anyOf[0]);
  });
});

describe("unionBranches", () => {
  it("returns undefined for a plain leaf", () => {
    expect(unionBranches({ type: "string" }, {})).toBeUndefined();
  });

  it("returns oneOf's branches", () => {
    const branches = [{ $ref: "#/$defs/DirectiveSourceSettings" }];
    expect(unionBranches({ oneOf: branches }, {})).toEqual(branches);
  });

  it("returns a bare anyOf's non-null branches, with no discriminator implied", () => {
    const node = { anyOf: [{ type: "string" }, { type: "integer" }] };
    expect(unionBranches(node, {})).toEqual(node.anyOf);
  });

  it("does not treat a single-branch anyOf (Optional[X], already unwrapped by resolveNode) as a union", () => {
    const node = { anyOf: [{ type: "string" }, { type: "null" }] };
    expect(unionBranches(node, {})).toBeUndefined();
  });
});

describe("discriminatorOf", () => {
  it("reads a well-formed discriminator", () => {
    const node = { discriminator: { propertyName: "type", mapping: { directive: "#/$defs/DirectiveSourceSettings" } } };
    expect(discriminatorOf(node)).toEqual({ propertyName: "type", mapping: { directive: "#/$defs/DirectiveSourceSettings" } });
  });

  it("returns undefined when there is none - the energy_cost Formula shape", () => {
    expect(discriminatorOf({ oneOf: [{ $ref: "#/$defs/MinimumFormula" }, { $ref: "#/$defs/TieredFormula" }] })).toBeUndefined();
  });
});

describe("schemaTypeName", () => {
  it("reads a $ref's own $defs entry name", () => {
    expect(schemaTypeName({ $ref: "#/$defs/Formula" })).toBe("Formula");
  });

  it("falls back to an inline schema's own title", () => {
    expect(schemaTypeName({ title: "Cost group" })).toBe("Cost group");
  });

  it("returns undefined for neither", () => {
    expect(schemaTypeName({ type: "string" })).toBeUndefined();
  });
});

describe("matchBranch", () => {
  const branches: JsonSchema[] = [
    { title: "Index", type: "object", properties: { kind: { const: "index" } } },
    { title: "Minimum", type: "object", properties: { kind: { const: "minimum" }, floor: { type: "number" } } },
  ];

  it("defaults to the first branch for a non-record value", () => {
    expect(matchBranch(null, branches, {})).toBe(0);
    expect(matchBranch("nope", branches, {})).toBe(0);
  });

  it("prefers a branch whose own const-tagged property matches the value's", () => {
    expect(matchBranch({ kind: "minimum", floor: 3 }, branches, {})).toBe(1);
  });

  it("resolves a $ref'd branch before checking its properties", () => {
    const root: JsonSchema = { $defs: { Minimum: branches[1]! } };
    const refBranches: JsonSchema[] = [branches[0]!, { $ref: "#/$defs/Minimum" }];
    expect(matchBranch({ kind: "minimum", floor: 3 }, refBranches, root)).toBe(1);
  });

  it("prefers the const-tag match even when every branch's required keys would equally match", () => {
    // Both branches here require only "kind", which every value has - a required-keys-only
    // match would ambiguously stop at the first branch regardless of which one actually fits;
    // the const tag is what correctly picks branch 1 instead.
    const required: JsonSchema[] = [
      { type: "object", properties: { kind: { const: "index" } }, required: ["kind"] },
      { type: "object", properties: { kind: { const: "minimum" }, floor: { type: "number" } }, required: ["kind"] },
    ];
    expect(matchBranch({ kind: "minimum", floor: 3 }, required, {})).toBe(1);
  });

  it("falls back to a branch whose required keys are all present, when no const tag matches", () => {
    const untagged: JsonSchema[] = [
      { type: "object", properties: { a: { type: "string" } }, required: ["a"] },
      { type: "object", properties: { b: { type: "string" } }, required: ["b"] },
    ];
    expect(matchBranch({ b: "x" }, untagged, {})).toBe(1);
  });

  it("defaults to the first branch when neither heuristic matches anything", () => {
    const untagged: JsonSchema[] = [
      { type: "object", properties: { a: { type: "string" } }, required: ["a"] },
      { type: "object", properties: { b: { type: "string" } }, required: ["b"] },
    ];
    expect(matchBranch({ c: "x" }, untagged, {})).toBe(0);
  });
});
