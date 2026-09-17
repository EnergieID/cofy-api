import { Validator } from "@cfworker/json-schema";

/** A JSON Schema, as it arrives from the API. */
export type JsonSchema = Record<string, unknown>;

/** One validation failure against a schema. */
export interface ValidationIssue {
  /** JSON Pointer to the offending value, e.g. `/source/api_key`. */
  pointer: string;
  message: string;
  keyword: string;
}

/**
 * Validate *value* against *schema*.
 *
 * The schema is narrowed to the instance's own union branches first - see
 * {@link narrowToInstance} - so a mistake reports against the type the user actually chose.
 */
export function validate(schema: JsonSchema, value: unknown): ValidationIssue[] {
  const narrowed = narrowToInstance(schema, value, schema);
  const validator = new Validator(narrowed, "2020-12", false);
  const result = validator.validate(value);
  if (result.valid) return [];

  return result.errors.map((error) => ({
    pointer: error.instanceLocation.replace(/^#/, ""),
    message: error.error,
    keyword: error.keyword,
  }));
}

/**
 * Replace every discriminated union along *value*'s shape with the branch *value* selects.
 *
 * JSON Schema has no discriminator - it is an OpenAPI keyword - so a validator has to try
 * all branches of a `oneOf` and report the failures of each. For a module with six possible
 * sources that turns one missing field into two dozen errors, all but one of them about a
 * source type the user never picked.
 *
 * The walk is driven by the instance rather than the schema, so it terminates even though
 * these schemas are recursive (a tariff formula can contain further formulas). Anything the
 * instance does not reach is left exactly as written, and a discriminator value with no
 * matching branch is left alone too - "matches no branch" is the correct message there.
 */
export function narrowToInstance(schema: JsonSchema, value: unknown, root: JsonSchema): JsonSchema {
  let node = deref(schema, root);

  const discriminator = node["discriminator"] as { propertyName?: string; mapping?: Record<string, string> } | undefined;
  if (Array.isArray(node["oneOf"]) && discriminator?.propertyName && isRecord(value)) {
    const tag = value[discriminator.propertyName];
    const ref = typeof tag === "string" ? discriminator.mapping?.[tag] : undefined;
    if (ref !== undefined) {
      node = deref({ $ref: ref }, root);
    }
  }

  const properties = node["properties"];
  if (isRecord(properties) && isRecord(value)) {
    const narrowed: Record<string, unknown> = {};
    for (const [key, sub] of Object.entries(properties)) {
      narrowed[key] =
        key in value && isRecord(sub) ? narrowToInstance(sub, value[key], root) : sub;
    }
    node = { ...node, properties: narrowed };
  }

  const items = node["items"];
  if (isRecord(items) && Array.isArray(value) && value.length > 0) {
    // Each element may select a different branch, so they are narrowed positionally.
    // `items: false` then bounds the array at exactly the elements described, which holds
    // because every element present has an entry.
    node = {
      ...node,
      prefixItems: value.map((item) => narrowToInstance(items, item, root)),
      items: false,
    };
  }

  return node;
}

/** Resolve a local `$ref` against the root schema's `$defs`, once. */
function deref(schema: JsonSchema, root: JsonSchema): JsonSchema {
  const ref = schema["$ref"];
  if (typeof ref !== "string" || !ref.startsWith("#/$defs/")) return schema;

  const defs = root["$defs"];
  if (!isRecord(defs)) return schema;

  const target = defs[ref.slice("#/$defs/".length)];
  if (!isRecord(target)) return schema;

  // The root's `$defs` has to travel with a narrowed branch: the branch is spliced in where
  // the union was, and whatever `$ref`s it still contains resolve against the root.
  return { ...target, $defs: defs };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
