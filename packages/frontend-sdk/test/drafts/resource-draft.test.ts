import { describe, expect, it } from "vitest";

import { ResourceDraft } from "../../src/drafts/resource-draft.js";
import { ResourceStore } from "../../src/stores/resource-store.js";
import { stubbedApi } from "../support/api.js";

const stored = { type: "source", name: "day_ahead", value: { type: "entsoe_day_ahead", api_key: { type: "secret", name: "entsoe_key" } } };

describe("ResourceDraft", () => {
  it("becomes dirty on a change and clean again on reset", () => {
    const draft = new ResourceDraft(stored);

    draft.set({ ...stored, description: "ENTSO-E" });
    expect(draft.dirty).toBe(true);

    draft.reset();
    expect(draft.dirty).toBe(false);
    expect(draft.current).toEqual(stored);
  });

  it("knows when an edit would rename the resource", () => {
    const draft = new ResourceDraft(stored);

    draft.set({ ...stored, name: "other" });

    expect(draft.renamed).toBe(true);
  });

  it("saves against the original name", async () => {
    const { api, calls } = stubbedApi((call) => ({ body: call.body }));
    const draft = new ResourceDraft(stored);
    draft.set({ ...stored, description: "ENTSO-E" });

    const saved = await draft.save(new ResourceStore(api), "test");

    expect(calls[0]).toMatchObject({ method: "PUT", path: "/management/communities/test/resources/day_ahead" });
    expect(saved).toEqual({ ...stored, description: "ENTSO-E" });
    expect(draft.saving).toBe(false);
  });
});
