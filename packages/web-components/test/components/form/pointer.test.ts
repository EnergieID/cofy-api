import { describe, expect, it } from "vitest";

import { getAtPointer, parsePointer, pointerFor, setAtPointer } from "../../../src/components/form/pointer.js";

describe("parsePointer", () => {
  it("splits a pointer into its segments", () => {
    expect(parsePointer("/source/api_key")).toEqual(["source", "api_key"]);
  });

  it("returns no segments for the root pointer", () => {
    expect(parsePointer("")).toEqual([]);
  });

  it("coerces a numeric segment to an array index", () => {
    expect(parsePointer("/formats/0/source")).toEqual(["formats", 0, "source"]);
  });

  it("decodes the escapes a JSON Pointer may contain", () => {
    expect(parsePointer("/a~1b")).toEqual(["a/b"]);
    expect(parsePointer("/a~0b")).toEqual(["a~b"]);
  });
});

describe("pointerFor", () => {
  it("appends a property segment", () => {
    expect(pointerFor("/source", "api_key")).toBe("/source/api_key");
  });

  it("appends an index segment", () => {
    expect(pointerFor("/formats", 0)).toBe("/formats/0");
  });

  it("escapes a segment that needs it", () => {
    expect(pointerFor("", "a/b")).toBe("/a~1b");
    expect(pointerFor("", "a~b")).toBe("/a~0b");
  });

  it("round-trips through parsePointer", () => {
    const pointer = pointerFor(pointerFor("", "source"), "api_key");
    expect(parsePointer(pointer)).toEqual(["source", "api_key"]);
  });
});

describe("getAtPointer", () => {
  const doc = { source: { type: "entsoe_day_ahead", api_key: "secret" }, formats: [{ type: "json" }] };

  it("reads a top-level value", () => {
    expect(getAtPointer(doc, "/formats")).toEqual([{ type: "json" }]);
  });

  it("reads a nested value", () => {
    expect(getAtPointer(doc, "/source/api_key")).toBe("secret");
  });

  it("reads an array element", () => {
    expect(getAtPointer(doc, "/formats/0/type")).toBe("json");
  });

  it("reads the whole document at the root pointer", () => {
    expect(getAtPointer(doc, "")).toBe(doc);
  });

  it("returns undefined for a path that does not exist", () => {
    expect(getAtPointer(doc, "/nope/missing")).toBeUndefined();
    expect(getAtPointer(doc, "/formats/5")).toBeUndefined();
  });
});

describe("setAtPointer", () => {
  it("sets a top-level value", () => {
    const doc = { name: "a" };
    expect(setAtPointer(doc, "/name", "b")).toEqual({ name: "b" });
  });

  it("sets a nested value without touching the original object", () => {
    const doc = { source: { api_key: "old" } };
    const next = setAtPointer(doc, "/source/api_key", "new") as typeof doc;

    expect(next).toEqual({ source: { api_key: "new" } });
    expect(doc.source.api_key).toBe("old");
  });

  it("replaces an array element by index", () => {
    const doc = { formats: [{ type: "json" }, { type: "csv" }] };
    const next = setAtPointer(doc, "/formats/1", { type: "kiwatt" });

    expect(next).toEqual({ formats: [{ type: "json" }, { type: "kiwatt" }] });
  });

  it("replaces the whole document at the root pointer", () => {
    expect(setAtPointer({ a: 1 }, "", { b: 2 })).toEqual({ b: 2 });
  });

  it("does not share structure with sibling branches it did not touch", () => {
    const doc = { source: { api_key: "x" }, formats: [{ type: "json" }] };
    const next = setAtPointer(doc, "/source/api_key", "y") as typeof doc;

    expect(next.formats).toBe(doc.formats);
  });
});
