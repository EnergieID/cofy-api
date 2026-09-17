import type { JsonSchema } from "@cofy/frontend-sdk";

import { deref } from "../../schema-ref.js";
import { parsePointer } from "./pointer.js";

/** A field's own label and description (`""` for neither), as read straight off its own schema. */
export interface FieldMeta {
  label: string;
  description: string;
}

/**
 * *schema*'s own label and description - resolved past its own `$ref` but no further, since a
 * field's `title`/`description` sit on the schema exactly as the property declares it (an
 * `Optional[X]`'s own wrapper, not whatever `X` resolves to - pydantic puts a field's annotation
 * there, not on the inner branch). The one place this is computed: `cofy-any-form` calls it once
 * per field and hands the result down as props, rather than every leaf/container re-deriving it
 * from a schema it would have to resolve itself.
 */
export function fieldMeta(schema: JsonSchema, root: JsonSchema, pointer: string): FieldMeta {
  const node = deref(schema, root);
  return {
    label: fieldLabel(node, pointer),
    description: typeof node["description"] === "string" ? node["description"] : "",
  };
}

/** A schema node's own title, or a title-cased fallback built from the field's own pointer segment. */
export function fieldLabel(node: JsonSchema, pointer: string): string {
  if (typeof node["title"] === "string") return node["title"];

  const last = parsePointer(pointer).at(-1);
  return typeof last === "string" ? titleCase(last) : "";
}

/** A JSON value is always a primitive here in practice; anything else falls back to JSON. */
export function primitiveText(value: unknown): string {
  if (value === null || value === undefined) return "";
  return typeof value === "string" || typeof value === "number" || typeof value === "boolean"
    ? String(value)
    : JSON.stringify(value);
}

function titleCase(name: string): string {
  return name
    .split(/[_\s]+/)
    .filter((word) => word.length > 0)
    .map((word) => word[0]!.toUpperCase() + word.slice(1))
    .join(" ");
}
