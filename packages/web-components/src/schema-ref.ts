import type { JsonSchema } from "@cofy/frontend-sdk";

/**
 * Schema nodes already being expanded on the current path, so a cyclic schema can be told apart
 * from a repeated sibling. Tracked by the resolved node's own identity rather than its `$ref`
 * string: the same `$defs` entry always derefs to the same object, so this works the same way
 * whether a walk starts from a raw `$ref` or from a node some earlier step already resolved -
 * a caller handed an already-resolved node has no `$ref` string left to track by.
 */
export type RefGuard = ReadonlySet<JsonSchema>;

export const noneExpanding: RefGuard = new Set();

/** *schema*'s own `$ref`, if it has one. */
export function refOf(schema: JsonSchema): string | undefined {
  return typeof schema["$ref"] === "string" ? schema["$ref"] : undefined;
}

/** Resolve a local `$ref` against the root schema's `$defs`, once - anything else passes through unresolved. */
export function deref(schema: JsonSchema, root: JsonSchema): JsonSchema {
  const ref = refOf(schema);
  if (ref === undefined || !ref.startsWith("#/$defs/")) return schema;

  const defs = root["$defs"];
  if (!isRecord(defs)) return schema;

  const target = defs[ref.slice("#/$defs/".length)];
  return isRecord(target) ? target : schema;
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
