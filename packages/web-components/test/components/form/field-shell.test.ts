import { describe, expect, it } from "vitest";

import { fieldLabel } from "../../../src/components/form/field-shell.js";

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
