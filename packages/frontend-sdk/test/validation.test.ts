import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { Validator } from "@cfworker/json-schema";

import { validate, type JsonSchema } from "../src/validation.js";

const schemas = JSON.parse(
  readFileSync(new URL("./fixtures/schemas.json", import.meta.url), "utf8"),
) as Record<string, JsonSchema>;

const tariff = schemas["tariff"]!;

function rawErrorCount(schema: JsonSchema, value: unknown): number {
  return new Validator(schema, "2020-12", false).validate(value).errors.length;
}

describe("validate", () => {
  it("accepts a valid module", () => {
    expect(
      validate(tariff, {
        type: "tariff",
        name: "spot",
        source: { type: "entsoe_day_ahead", api_key: "k", country_code: "BE" },
      }),
    ).toEqual([]);
  });

  it("reports a missing field on the chosen source, and nothing about the others", () => {
    const value = { type: "tariff", name: "spot", source: { type: "entsoe_day_ahead" } };

    const issues = validate(tariff, value);

    expect(issues.map((i) => i.pointer)).toContain("/source");
    expect(issues.some((i) => i.message.includes("api_key"))).toBe(true);
    // nothing about branches the user did not pick
    const text = issues.map((i) => i.message).join(" ");
    expect(text).not.toContain("boundaries");
    expect(text).not.toContain("record_id");
    expect(text).not.toContain("dynamic_boundary_directive");
  });

  it("cuts the noise an unnarrowed validator produces", () => {
    const value = { type: "tariff", name: "spot", source: { type: "entsoe_day_ahead" } };

    expect(validate(tariff, value).length).toBeLessThan(rawErrorCount(tariff, value) / 4);
  });

  it("reports a wrongly typed field on the chosen source", () => {
    const issues = validate(tariff, {
      type: "tariff",
      name: "spot",
      source: { type: "entsoe_day_ahead", api_key: "k", country_code: [1] },
    });

    expect(issues.some((i) => i.pointer === "/source/country_code")).toBe(true);
  });

  it("leaves an unknown discriminator value to report as matching no branch", () => {
    const issues = validate(tariff, { type: "tariff", name: "spot", source: { type: "nope" } });

    expect(issues.some((i) => i.pointer === "/source")).toBe(true);
  });

  it("narrows each element of a list of unions independently", () => {
    const issues = validate(tariff, {
      type: "tariff",
      name: "spot",
      source: { type: "entsoe_day_ahead", api_key: "k" },
      formats: [{ type: "kiwatt", source: "s" }, { type: "csv" }],
    });

    expect(issues).toEqual([]);
  });

  it("reports the offending element of a list, against that element's own branch", () => {
    const issues = validate(tariff, {
      type: "tariff",
      name: "spot",
      source: { type: "entsoe_day_ahead", api_key: "k" },
      formats: [{ type: "csv" }, { type: "kiwatt", source: 123 }],
    });

    expect(issues.some((i) => i.pointer === "/formats/1/source")).toBe(true);
    // and nothing about the csv element, which is fine
    expect(issues.every((i) => !i.pointer.startsWith("/formats/0"))).toBe(true);
  });

  it("terminates on a recursive schema", () => {
    const issues = validate(tariff, {
      type: "tariff",
      name: "spot",
      source: {
        type: "energy_cost",
        tariff: [
          {
            start: "2026-01-01T00:00:00Z",
            consumption: {
              total: { kind: "scheduled", schedule: [{ formula: { kind: "index", constant_cost: 1 } }] },
            },
          },
        ],
      },
    });

    expect(Array.isArray(issues)).toBe(true);
  });

  it("catches a bad top-level field", () => {
    const issues = validate(tariff, {
      type: "tariff",
      name: "has spaces",
      source: { type: "entsoe_day_ahead", api_key: "k" },
    });

    expect(issues.some((i) => i.pointer === "/name")).toBe(true);
  });
});
