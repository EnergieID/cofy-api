import type { ValidationIssue } from "@cofy/frontend-sdk";

/** Issues reported exactly at *pointer* - what a leaf field, or a container's own failed union match, shows. */
export function issuesAt(issues: readonly ValidationIssue[], pointer: string): ValidationIssue[] {
  return issues.filter((issue) => issue.pointer === pointer);
}

/** Issues at *pointer* or anywhere below it - for a container's "problems inside" rollup. */
export function issuesBelow(issues: readonly ValidationIssue[], pointer: string): ValidationIssue[] {
  const prefix = pointer === "" ? "/" : `${pointer}/`;
  return issues.filter((issue) => issue.pointer === pointer || issue.pointer.startsWith(prefix));
}
