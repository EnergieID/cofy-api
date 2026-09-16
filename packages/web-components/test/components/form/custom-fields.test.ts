import { describe, expect, it } from "vitest";

import { createFieldRegistry, defaultFieldRegistry } from "../../../src/components/form/custom-fields.js";

describe("defaultFieldRegistry", () => {
  it("registers nothing", () => {
    expect(defaultFieldRegistry.customFieldFor("Formula")).toBeUndefined();
    expect(defaultFieldRegistry.customFieldFor(undefined)).toBeUndefined();
  });
});

describe("createFieldRegistry", () => {
  it("looks up a registered type name", () => {
    const registry = createFieldRegistry({ Formula: "cofy-formula-form" });

    expect(registry.customFieldFor("Formula")).toBe("cofy-formula-form");
  });

  it("falls through for an unregistered type name", () => {
    const registry = createFieldRegistry({ Formula: "cofy-formula-form" });

    expect(registry.customFieldFor("DirectiveSourceSettings")).toBeUndefined();
  });

  it("falls through when there is no type name at all", () => {
    const registry = createFieldRegistry({ Formula: "cofy-formula-form" });

    expect(registry.customFieldFor(undefined)).toBeUndefined();
  });
});
