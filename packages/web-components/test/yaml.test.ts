import { describe, expect, it } from "vitest";

import { toYaml, withoutNulls } from "../src/yaml.js";

describe("withoutNulls", () => {
  it("drops keys whose value is null", () => {
    expect(withoutNulls({ name: "spot", display_name: null })).toEqual({ name: "spot" });
  });

  it("keeps everything else, including falsy values that mean something", () => {
    expect(withoutNulls({ enabled: false, count: 0, label: "" })).toEqual({ enabled: false, count: 0, label: "" });
  });

  it("recurses into nested objects", () => {
    expect(withoutNulls({ source: { type: "entsoe_day_ahead", country_code: null } })).toEqual({
      source: { type: "entsoe_day_ahead" },
    });
  });

  it("recurses into arrays", () => {
    expect(withoutNulls({ formats: [{ type: "csv", source: null }] })).toEqual({ formats: [{ type: "csv" }] });
  });

  it("leaves a top-level null alone", () => {
    expect(withoutNulls(null)).toBeNull();
  });
});

describe("toYaml", () => {
  it("omits unset fields rather than spelling them out as null", () => {
    const yaml = toYaml({ type: "tariff", name: "spot", display_name: null, description: null });

    expect(yaml).toBe("type: tariff\nname: spot\n");
  });

  it("keeps the declared field order rather than sorting", () => {
    const yaml = toYaml({ type: "tariff", name: "spot", source: { type: "entsoe_day_ahead", api_key: "k" } });

    expect(yaml.split("\n").slice(0, 3)).toEqual(["type: tariff", "name: spot", "source:"]);
  });
});
