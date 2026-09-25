import { describe, expect, it } from "vitest";

import { ModuleDraft } from "../../src/drafts/module-draft.js";
import { ModuleStore } from "../../src/stores/module-store.js";
import { validate, type JsonSchema } from "../../src/validation.js";
import { readFileSync } from "node:fs";
import { stubbedApi } from "../support/api.js";

const schemas = JSON.parse(
  readFileSync(new URL("../fixtures/schemas.json", import.meta.url), "utf8"),
) as Record<string, JsonSchema>;

const stored = {
  type: "tariff",
  name: "spot",
  source: { type: "entsoe_day_ahead", api_key: "**********", country_code: "BE" },
};

describe("ModuleDraft", () => {
  it("starts clean and valid-looking", () => {
    const draft = new ModuleDraft(stored);

    expect(draft.dirty).toBe(false);
    expect(draft.issues).toEqual([]);
    expect(draft.current).toEqual(stored);
  });

  it("does not share structure with the module it was opened from", () => {
    const draft = new ModuleDraft(stored);

    (draft.current["source"] as Record<string, unknown>)["country_code"] = "NL";

    expect((stored.source as Record<string, unknown>)["country_code"]).toBe("BE");
    expect((draft.original["source"] as Record<string, unknown>)["country_code"]).toBe("BE");
  });

  it("becomes dirty on a change and clean again on reset", () => {
    const draft = new ModuleDraft(stored);

    draft.set({ ...stored, display_name: "Spot" });
    expect(draft.dirty).toBe(true);

    draft.reset();
    expect(draft.dirty).toBe(false);
    expect(draft.current).toEqual(stored);
  });

  it("keeps the identity it was opened with, so a rename is visible", () => {
    const draft = new ModuleDraft(stored);

    draft.set({ ...stored, name: "renamed" });

    expect(draft.id).toEqual({ type: "tariff", name: "spot" });
    expect(draft.renamed).toBe(true);
  });

  it("records validation issues against the catalog schema", () => {
    const draft = new ModuleDraft({ type: "tariff", name: "spot", source: { type: "entsoe_day_ahead" } });

    const issues = draft.check(schemas["tariff"]!);

    expect(issues.length).toBeGreaterThan(0);
    expect(draft.valid).toBe(false);
    expect(issues).toEqual(validate(schemas["tariff"]!, draft.current));
  });

  it("is valid once the missing field is supplied", () => {
    const draft = new ModuleDraft(stored);

    draft.check(schemas["tariff"]!);

    expect(draft.valid).toBe(true);
  });

  it("saves through the store against its original identity", async () => {
    const { api, calls } = stubbedApi((call) => (call.method === "PUT" ? { body: call.body } : { body: [stored] }));
    const store = new ModuleStore(api);
    await store.load("test");
    const draft = new ModuleDraft(stored);
    draft.set({ ...stored, display_name: "Spot prices" });

    const saved = await draft.save(store, "test");

    expect(calls.at(-1)!.path).toBe("/management/communities/test/modules/tariff/spot");
    expect(saved["display_name"]).toBe("Spot prices");
    expect(store.find("test", { type: "tariff", name: "spot" })).toEqual(saved);
    expect(draft.saving).toBe(false);
  });

  it("clears the saving flag when the save fails", async () => {
    const { api } = stubbedApi((call) =>
      call.method === "PUT" ? { status: 409, body: { status: 409, detail: "exists" } } : { body: [stored] },
    );
    const store = new ModuleStore(api);
    const draft = new ModuleDraft(stored);

    await expect(draft.save(store, "test")).rejects.toThrow("exists");
    expect(draft.saving).toBe(false);
  });
});
