import { describe, expect, it } from "vitest";

import { locate } from "../src/components/cofy-yaml-editor.js";

const document = `type: tariff
name: spot
source:
  type: entsoe_day_ahead
  api_key: "**********"
formats:
  - type: kiwatt
    source: Cofy-API-Demo
`;

describe("locate", () => {
  it("finds a top-level value", () => {
    const range = locate(document, "/name")!;
    expect(document.slice(range[0], range[1])).toBe("spot");
  });

  it("finds a nested value through its path, not by name", () => {
    // `source` appears twice in this document; the pointer has to pick the right one
    const range = locate(document, "/source/type")!;
    expect(document.slice(range[0], range[1])).toBe("entsoe_day_ahead");
  });

  it("finds a value inside a list", () => {
    const range = locate(document, "/formats/0/source")!;
    expect(document.slice(range[0], range[1])).toBe("Cofy-API-Demo");
  });

  it("returns nothing for a path the document does not have", () => {
    expect(locate(document, "/nope/missing")).toBeNull();
  });

  it("returns nothing for the document root", () => {
    expect(locate(document, "")).toBeNull();
  });

  it("returns nothing when the document does not parse", () => {
    expect(locate("key: [unclosed", "/key")).toBeNull();
  });

  it("decodes the escapes a JSON Pointer may contain", () => {
    const escaped = 'a/b: 1\na~b: 2\n';
    expect(escaped.slice(...locate(escaped, "/a~1b")!)).toBe("1");
    expect(escaped.slice(...locate(escaped, "/a~0b")!)).toBe("2");
  });
});
