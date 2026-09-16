import type { JsonSchema } from "@cofy/frontend-sdk";

import { deref, isRecord, refOf } from "../../schema-ref.js";

/** An OpenAPI-style discriminator, tying a union's branches to a tag property. */
export interface Discriminator {
  propertyName: string;
  mapping: Readonly<Record<string, string>>;
}

/**
 * What kind of control a schema node should render as.
 *
 * `schema` on a variant is the node the next step should render - already resolved past this
 * node's own `$ref`/`anyOf`-nullable-unwrap, so a caller never has to re-derive it.
 */
export type FieldKind =
  | { kind: "union"; schema: JsonSchema; branches: readonly JsonSchema[]; discriminator?: Discriminator }
  | { kind: "enum"; schema: JsonSchema; values: readonly unknown[] }
  | { kind: "const"; value: unknown }
  | { kind: "secret" }
  | { kind: "string" }
  | { kind: "number" }
  | { kind: "boolean" }
  | { kind: "object"; schema: JsonSchema }
  | { kind: "array"; schema: JsonSchema; items: JsonSchema }
  | { kind: "unknown"; schema: JsonSchema };

/**
 * Decide how a schema node should render, resolving its own `$ref` first.
 *
 * `oneOf` and a multi-branch `anyOf` both render as a union - pydantic only ever puts a
 * `discriminator` beside `oneOf`, so `anyOf` unions render as the no-discriminator fallback.
 * An `anyOf` with exactly one non-null branch is `Optional[X]`: it is not a union at all, it
 * unwraps straight through to whatever `X` resolves to.
 */
export function resolveFieldKind(schema: JsonSchema, root: JsonSchema): FieldKind {
  const node = deref(schema, root);

  const oneOf = node["oneOf"];
  if (Array.isArray(oneOf) && oneOf.length > 0) {
    return { kind: "union", schema: node, branches: oneOf as JsonSchema[], discriminator: discriminatorOf(node) };
  }

  const anyOf = node["anyOf"];
  if (Array.isArray(anyOf) && anyOf.length > 0) {
    const nonNull = (anyOf as JsonSchema[]).filter((branch) => deref(branch, root)["type"] !== "null");
    if (nonNull.length > 1) return { kind: "union", schema: node, branches: nonNull };
    if (nonNull.length === 1) return resolveFieldKind(nonNull[0]!, root);
  }

  if (Array.isArray(node["enum"])) return { kind: "enum", schema: node, values: node["enum"] as unknown[] };
  if ("const" in node) return { kind: "const", value: node["const"] };
  if (node["type"] === "string" && node["format"] === "password" && node["writeOnly"] === true) {
    return { kind: "secret" };
  }

  switch (node["type"]) {
    case "string":
      return { kind: "string" };
    case "integer":
    case "number":
      return { kind: "number" };
    case "boolean":
      return { kind: "boolean" };
    case "object":
      // A `dict[str, X]` schema (`additionalProperties`, no fixed `properties`) has no keys the
      // generic object renderer could draw a field for - shown as raw YAML until a dedicated
      // field exists for it, rather than silently rendering nothing.
      return isRecord(node["properties"]) ? { kind: "object", schema: node } : { kind: "unknown", schema: node };
    case "array": {
      const items = node["items"];
      return { kind: "array", schema: node, items: isRecord(items) ? items : {} };
    }
    default:
      return { kind: "unknown", schema: node };
  }
}

/**
 * The name a custom field registry would key this schema under - its own `$ref`'s `$defs`
 * entry, or its own `title` for an inline schema with no `$ref`.
 */
export function schemaTypeName(schema: JsonSchema): string | undefined {
  const ref = refOf(schema);
  if (ref !== undefined) return ref.split("/").pop();
  return typeof schema["title"] === "string" ? schema["title"] : undefined;
}

function discriminatorOf(node: JsonSchema): Discriminator | undefined {
  const discriminator = node["discriminator"];
  if (!isRecord(discriminator)) return undefined;

  const propertyName = discriminator["propertyName"];
  const mapping = discriminator["mapping"];
  if (typeof propertyName !== "string" || !isRecord(mapping)) return undefined;

  return { propertyName, mapping: mapping as Record<string, string> };
}
