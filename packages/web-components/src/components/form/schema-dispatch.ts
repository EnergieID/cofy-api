import type { JsonSchema } from "@cofy/frontend-sdk";

import { deref, isRecord, refOf } from "../../schema-ref.js";

/** An OpenAPI-style discriminator, tying a union's branches to a tag property. */
export interface Discriminator {
  propertyName: string;
  mapping: Readonly<Record<string, string>>;
}

/**
 * *schema* resolved past its own `$ref` and, if it is `Optional[X]` (an `anyOf` with exactly one
 * non-`null` branch), past that wrapper too - recursively, so however deep the `Optional`/`$ref`
 * nesting goes, the result still bottoms out. What is left is either a concrete leaf/object/array
 * node, or a genuine union (`oneOf`, or an `anyOf` with more than one non-`null` branch) - the
 * shape every field mapper and container field actually needs to inspect.
 */
export function resolveNode(schema: JsonSchema, root: JsonSchema): JsonSchema {
  const node = deref(schema, root);

  if (Array.isArray(node["oneOf"]) && (node["oneOf"] as unknown[]).length > 0) return node;

  const anyOf = node["anyOf"];
  if (Array.isArray(anyOf) && anyOf.length > 0) {
    const nonNull = (anyOf as JsonSchema[]).filter((branch) => deref(branch, root)["type"] !== "null");
    if (nonNull.length === 1) return resolveNode(nonNull[0]!, root);
    if (nonNull.length > 1) return node;
  }

  return node;
}

/**
 * *node*'s own union branches - `oneOf`, or an `anyOf` with more than one non-`null` branch - or
 * `undefined` if it isn't one. Expects *node* already resolved by {@link resolveNode}.
 */
export function unionBranches(node: JsonSchema, root: JsonSchema): readonly JsonSchema[] | undefined {
  const oneOf = node["oneOf"];
  if (Array.isArray(oneOf) && oneOf.length > 0) return oneOf as JsonSchema[];

  const anyOf = node["anyOf"];
  if (Array.isArray(anyOf)) {
    const nonNull = (anyOf as JsonSchema[]).filter((branch) => deref(branch, root)["type"] !== "null");
    if (nonNull.length > 1) return nonNull;
  }

  return undefined;
}

/**
 * *node*'s own discriminator, if it has one - pydantic only ever puts a `discriminator` beside
 * `oneOf`, never a bare `anyOf` union.
 */
export function discriminatorOf(node: JsonSchema): Discriminator | undefined {
  const discriminator = node["discriminator"];
  if (!isRecord(discriminator)) return undefined;

  const propertyName = discriminator["propertyName"];
  const mapping = discriminator["mapping"];
  if (typeof propertyName !== "string" || !isRecord(mapping)) return undefined;

  return { propertyName, mapping: mapping as Record<string, string> };
}

/**
 * The name a custom field mapper would key this schema under - its own `$ref`'s `$defs` entry,
 * or its own `title` for an inline schema with no `$ref`. Checked against *schema* as handed
 * down, before {@link resolveNode} resolves it - the identity a `$ref` carries (`TimeseriesSource`,
 * `Formula`, ...) is exactly what resolving it throws away.
 */
export function schemaTypeName(schema: JsonSchema): string | undefined {
  const ref = refOf(schema);
  if (ref !== undefined) return ref.split("/").pop();
  return typeof schema["title"] === "string" ? schema["title"] : undefined;
}
