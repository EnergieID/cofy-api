import type { JsonSchema, Referable, ResourceRef } from "@cofy/frontend-sdk";

import { isRecord } from "./ref.js";

/** What *node* accepts a reference to, if it is a referable field. */
export function referableOf(node: JsonSchema): Referable | undefined {
  const referable = node["x-referable"];
  if (!isRecord(referable) || typeof referable["kind"] !== "string") return undefined;
  const types = referable["types"];
  return Array.isArray(types)
    ? { kind: referable["kind"], types: types.filter((type): type is string => typeof type === "string") }
    : { kind: referable["kind"] };
}

/** A referable field's two branches: its value first, the reference to a resource second. */
export function referableBranches(node: JsonSchema): { value: JsonSchema; ref: JsonSchema } | undefined {
  const branches = node["oneOf"];
  if (!Array.isArray(branches) || branches.length !== 2) return undefined;
  const [value, ref] = branches as unknown[];
  return isRecord(value) && isRecord(ref) ? { value, ref } : undefined;
}

/** Whether *value* is a reference to a resource rather than a value itself. */
export function isRefValue(value: unknown): value is ResourceRef {
  return isRecord(value) && value["type"] === "ref";
}
