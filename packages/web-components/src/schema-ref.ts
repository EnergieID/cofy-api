import type { JsonSchema } from "@cofy/frontend-sdk";

/** `$ref`s already being expanded on the current path, so a cyclic schema can be told apart from a repeated sibling. */
export type RefGuard = ReadonlySet<string>;

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
