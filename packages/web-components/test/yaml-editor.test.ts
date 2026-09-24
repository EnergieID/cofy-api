import { beforeEach, describe, expect, it, vi } from "vitest";
import type * as CodemirrorLint from "@codemirror/lint";

vi.mock("@codemirror/lint", async (importOriginal) => {
  const actual = await importOriginal<typeof CodemirrorLint>();
  return { ...actual, forceLinting: vi.fn(actual.forceLinting) };
});

import { forceLinting } from "@codemirror/lint";

import type { CofyYamlEditor } from "../src/components/editor/cofy-yaml-editor.js";
import { locate } from "../src/components/editor/cofy-yaml-editor.js";

async function mountEditor(text: string): Promise<CofyYamlEditor> {
  // `document` below is this file's own YAML fixture text, not the DOM global - `globalThis`
  // reaches the real one instead of shadowing into it.
  const element = globalThis.document.createElement("cofy-yaml-editor");
  element.text = text;
  globalThis.document.body.append(element);
  await element.updateComplete;
  return element;
}

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

describe("cofy-yaml-editor's issues property", () => {
  beforeEach(() => {
    globalThis.document.body.replaceChildren();
  });

  it("re-runs the linter when new issues arrive with no text change", async () => {
    const element = await mountEditor(document);
    vi.mocked(forceLinting).mockClear(); // drop whatever mounting itself triggered

    element.issues = [{ pointer: "/name", message: "not allowed" }];
    await element.updateComplete;

    // A plain CodeMirror `dispatch({})` satisfies none of the linter extension's own rerun
    // conditions (docChanged, a config change, or `needsRefresh`) - only `forceLinting` does.
    expect(forceLinting).toHaveBeenCalledTimes(1);
  });

  it("does not re-run the linter merely because the text prop is reassigned to its own value", async () => {
    const element = await mountEditor(document);
    vi.mocked(forceLinting).mockClear(); // drop whatever mounting itself triggered

    element.text = document; // same value - the editor's own doc does not actually change
    await element.updateComplete;

    expect(forceLinting).not.toHaveBeenCalled();
  });
});
