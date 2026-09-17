import { describe, expect, it } from "vitest";
import type { JsonSchema } from "@cofy/frontend-sdk";

import { fieldLabel, fieldMeta } from "../../../src/components/form/field-shell.js";

describe("fieldLabel", () => {
  it("uses the schema's own title when it has one", () => {
    expect(fieldLabel({ title: "Api Key" }, "/source/api_key")).toBe("Api Key");
  });

  it("falls back to a title-cased property name", () => {
    expect(fieldLabel({}, "/country_code")).toBe("Country Code");
  });

  it("returns an empty label when the last segment is an array index, not a name", () => {
    // A row's own label is a container's job (e.g. "Item 1"), not this fallback's.
    expect(fieldLabel({}, "/formats/0")).toBe("");
  });

  it("returns an empty label for the document root", () => {
    expect(fieldLabel({}, "")).toBe("");
  });
});

describe("fieldMeta", () => {
  it("reads the schema's own title and description", () => {
    const schema = { title: "Api Key", description: "Used to authenticate." };
    expect(fieldMeta(schema, {}, "/source/api_key")).toEqual({ label: "Api Key", description: "Used to authenticate." });
  });

  it("returns an empty description when there is none", () => {
    expect(fieldMeta({ title: "Api Key" }, {}, "/source/api_key")).toEqual({ label: "Api Key", description: "" });
  });

  it("resolves a local $ref first", () => {
    const costGroup = { title: "Cost Group", description: "Which tariff bracket this belongs to." };
    const root: JsonSchema = { $defs: { CostGroup: costGroup } };
    expect(fieldMeta({ $ref: "#/$defs/CostGroup" }, root, "/cost_group")).toEqual({
      label: "Cost Group",
      description: "Which tariff bracket this belongs to.",
    });
  });

  it("reads an Optional wrapper's own title/description rather than the type it resolves to - pydantic puts a field's annotation there, not on the inner branch", () => {
    const costGroup = { title: "Cost Group Type", enum: ["low", "high"] };
    const root: JsonSchema = { $defs: { CostGroup: costGroup } };
    const schema = {
      title: "Display Cost Group",
      description: "Shown to the reader.",
      anyOf: [{ $ref: "#/$defs/CostGroup" }, { type: "null" }],
      default: null,
    };

    expect(fieldMeta(schema, root, "/display_cost_group")).toEqual({
      label: "Display Cost Group",
      description: "Shown to the reader.",
    });
  });
});
