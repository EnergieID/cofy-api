import { describe, expect, it } from "vitest";
import type { ValidationIssue } from "@cofy/frontend-sdk";

import { issuesAt, issuesBelow } from "../../../src/components/form/issues.js";

const issues: ValidationIssue[] = [
  { pointer: "/source", message: "does not match a branch", keyword: "oneOf" },
  { pointer: "/source/api_key", message: "required", keyword: "required" },
  { pointer: "/formats/0/type", message: "wrong type", keyword: "type" },
  { pointer: "/formats/1/type", message: "wrong type", keyword: "type" },
];

describe("issuesAt", () => {
  it("matches only the exact pointer", () => {
    expect(issuesAt(issues, "/source/api_key")).toEqual([issues[1]]);
  });

  it("does not match a descendant's issue", () => {
    expect(issuesAt(issues, "/source")).toEqual([issues[0]]);
  });

  it("returns nothing for a pointer with no issue", () => {
    expect(issuesAt(issues, "/name")).toEqual([]);
  });
});

describe("issuesBelow", () => {
  it("includes the container's own issue and everything nested under it", () => {
    expect(issuesBelow(issues, "/source")).toEqual([issues[0], issues[1]]);
  });

  it("includes every array element's issues at the array's own pointer", () => {
    expect(issuesBelow(issues, "/formats")).toEqual([issues[2], issues[3]]);
  });

  it("does not match a sibling that merely shares a prefix", () => {
    expect(issuesBelow(issues, "/format")).toEqual([]);
  });

  it("includes everything at the root", () => {
    expect(issuesBelow(issues, "")).toEqual(issues);
  });
});
