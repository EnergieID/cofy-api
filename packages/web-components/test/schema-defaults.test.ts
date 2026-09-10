import { describe, expect, it } from "vitest";

import { seedFromSchema } from "../src/schema-defaults.js";

describe("seedFromSchema", () => {
  it("uses a property's default", () => {
    const seeded = seedFromSchema({
      type: "object",
      properties: { name: { type: "string", default: "default" } },
    });

    expect(seeded).toEqual({ name: "default" });
  });

  it("includes required properties without a default, as empty placeholders", () => {
    const seeded = seedFromSchema({
      type: "object",
      properties: { api_key: { type: "string" }, count: { type: "integer" }, on: { type: "boolean" } },
      required: ["api_key", "count", "on"],
    });

    expect(seeded).toEqual({ api_key: "", count: 0, on: false });
  });

  it("leaves out properties that are neither required nor defaulted", () => {
    const seeded = seedFromSchema({
      type: "object",
      properties: { name: { type: "string" }, optional: { type: "string" } },
      required: ["name"],
    });

    expect(seeded).toEqual({ name: "" });
  });

  it("pins a const, which is how a discriminator gets its value", () => {
    const seeded = seedFromSchema({
      type: "object",
      properties: { type: { const: "tariff", default: "tariff" } },
      required: ["type"],
    });

    expect(seeded).toEqual({ type: "tariff" });
  });

  it("follows a $ref into the schema's own $defs", () => {
    const seeded = seedFromSchema({
      type: "object",
      properties: { source: { $ref: "#/$defs/Source" } },
      required: ["source"],
      $defs: { Source: { type: "object", properties: { type: { const: "x", default: "x" } }, required: ["type"] } },
    });

    expect(seeded).toEqual({ source: { type: "x" } });
  });

  it("takes the first branch of a union, which the author can then change", () => {
    const seeded = seedFromSchema({
      type: "object",
      properties: {
        source: {
          oneOf: [{ $ref: "#/$defs/A" }, { $ref: "#/$defs/B" }],
        },
      },
      required: ["source"],
      $defs: {
        A: { type: "object", properties: { type: { const: "a", default: "a" } }, required: ["type"] },
        B: { type: "object", properties: { type: { const: "b", default: "b" } }, required: ["type"] },
      },
    });

    expect(seeded).toEqual({ source: { type: "a" } });
  });

  it("starts arrays empty", () => {
    expect(seedFromSchema({ type: "object", properties: { xs: { type: "array" } }, required: ["xs"] })).toEqual({
      xs: [],
    });
  });

  it("terminates on a schema that refers back to itself", () => {
    // Real module schemas are recursive - a tariff formula can contain further formulas -
    // and seeding walks the schema rather than an instance, so it needs a stop.
    const seeded = seedFromSchema({
      type: "object",
      properties: { formula: { $ref: "#/$defs/Formula" } },
      required: ["formula"],
      $defs: {
        Formula: {
          type: "object",
          properties: { kind: { const: "index", default: "index" }, inner: { $ref: "#/$defs/Formula" } },
          required: ["kind", "inner"],
        },
      },
    });

    expect(seeded).toEqual({ formula: { kind: "index", inner: null } });
  });

  it("terminates on mutual recursion between two definitions", () => {
    const seeded = seedFromSchema({
      type: "object",
      properties: { a: { $ref: "#/$defs/A" } },
      required: ["a"],
      $defs: {
        A: { type: "object", properties: { b: { $ref: "#/$defs/B" } }, required: ["b"] },
        B: { type: "object", properties: { a: { $ref: "#/$defs/A" } }, required: ["a"] },
      },
    });

    expect(seeded).toEqual({ a: { b: { a: null } } });
  });

  it("returns an empty object for a schema with no properties", () => {
    expect(seedFromSchema({ type: "object" })).toEqual({});
  });
});
