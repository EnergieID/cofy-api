import type { JsonSchema } from "@cofy/frontend-sdk";

import { isRecord } from "./ref.js";
import { parsePointer } from "./pointer.js";

/** A JSON value is always a primitive here in practice; anything else falls back to JSON. */
export function primitiveText(value: unknown): string {
  if (value === null || value === undefined) return "";
  return typeof value === "string" || typeof value === "number" || typeof value === "boolean"
    ? String(value)
    : JSON.stringify(value);
}

/** Title-cases an underscored/spaced name (a property name, a `type`/`kind` tag) for display. */
export function titleCase(name: string): string {
  return name
    .split(/[_\s]+/)
    .filter((word) => word.length > 0)
    .map((word) => word[0]!.toUpperCase() + word.slice(1))
    .join(" ");
}

/** A schema node's own title, or a title-cased fallback built from the field's own pointer segment. */
export function fieldLabel(node: JsonSchema, pointer: string): string {
  if (typeof node["title"] === "string") return node["title"];

  const last = parsePointer(pointer).at(-1);
  return typeof last === "string" ? titleCase(last) : "";
}

/** A schema node's own description, or `""` if it has none. */
export function fieldDescription(node: JsonSchema): string {
  return typeof node["description"] === "string" ? node["description"] : "";
}

/**
 * *value*'s own `type` or `kind` property, if it has a string one - the discriminator tag every
 * polymorphic shape in this schema family is keyed by (a module/source's `type`, a formula's
 * `kind`) - title-cased for display. Falls back to *node*'s own `title` when neither tag is
 * present. Read directly off the value rather than matched against the schema's own `const`
 * declarations: a union's value already carries whichever branch's tag once chosen, so this one
 * check covers both an object's own summary and a union's, with no branch resolution needed.
 */
export function tagSummary(value: unknown, node: JsonSchema): string | undefined {
  if (!isRecord(value)) return undefined;

  const tag = value["type"] ?? value["kind"];
  if (typeof tag === "string") return titleCase(tag);

  const title = node["title"];
  return typeof title === "string" ? title : undefined;
}

/** An array's own length, as a one-line stand-in for a collapsed list. */
export function arraySummary(value: unknown): string | undefined {
  return Array.isArray(value) ? value.length.toString() : undefined;
}

/** A dict's own entry count, as a one-line stand-in for a collapsed dict. */
export function dictSummary(value: unknown): string | undefined {
  return isRecord(value) ? Object.keys(value).length.toString() : undefined;
}
