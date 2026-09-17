import { describe, expect, it } from "vitest";

import {
  arraySummary,
  fieldDescription,
  fieldLabel,
  primitiveText,
  tagSummary,
  titleCase,
} from "../../../../src/components/form/schema/summary.js";

describe("primitiveText", () => {
  it("stringifies a string, number, and boolean", () => {
    expect(primitiveText("spot")).toBe("spot");
    expect(primitiveText(3)).toBe("3");
    expect(primitiveText(false)).toBe("false");
  });

  it("returns an empty string for null/undefined", () => {
    expect(primitiveText(null)).toBe("");
    expect(primitiveText(undefined)).toBe("");
  });

  it("falls back to JSON for anything else", () => {
    expect(primitiveText({ a: 1 })).toBe('{"a":1}');
  });
});

describe("titleCase", () => {
  it("title-cases an underscored name", () => {
    expect(titleCase("entsoe_day_ahead")).toBe("Entsoe Day Ahead");
  });

  it("title-cases a single word", () => {
    expect(titleCase("csv")).toBe("Csv");
  });
});

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

describe("fieldDescription", () => {
  it("reads the schema's own description", () => {
    expect(fieldDescription({ description: "Used to authenticate." })).toBe("Used to authenticate.");
  });

  it("returns an empty string when there is none", () => {
    expect(fieldDescription({ title: "Api Key" })).toBe("");
  });
});

describe("tagSummary", () => {
  it("reads the value's own type, title-cased", () => {
    expect(tagSummary({ type: "day_ahead" }, {})).toBe("Day Ahead");
  });

  it("falls back to kind when there is no type", () => {
    expect(tagSummary({ kind: "minimum_formula" }, {})).toBe("Minimum Formula");
  });

  it("prefers type over kind when a value somehow has both", () => {
    expect(tagSummary({ type: "a", kind: "b" }, {})).toBe("A");
  });

  it("falls back to the resolved node's own title when the value has neither tag", () => {
    expect(tagSummary({ name: "spot" }, { title: "Nested Thing" })).toBe("Nested Thing");
  });

  it("returns undefined when there is no tag and no title either", () => {
    expect(tagSummary({ name: "spot" }, {})).toBeUndefined();
  });

  it("returns undefined for a non-record value, regardless of the node's own title", () => {
    expect(tagSummary(null, { title: "Nested Thing" })).toBeUndefined();
    expect(tagSummary("spot", { title: "Nested Thing" })).toBeUndefined();
  });
});

describe("arraySummary", () => {
  it("returns the array's own length as a string", () => {
    expect(arraySummary(["a", "b", "c"])).toBe("3");
    expect(arraySummary([])).toBe("0");
  });

  it("returns undefined for a non-array value", () => {
    expect(arraySummary(null)).toBeUndefined();
    expect(arraySummary({ length: 3 })).toBeUndefined();
  });
});
