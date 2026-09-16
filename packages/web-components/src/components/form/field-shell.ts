import type { JsonSchema } from "@cofy/frontend-sdk";

import { parsePointer } from "./pointer.js";

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
