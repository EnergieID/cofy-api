import { stringify } from "yaml";

/**
 * Render a value as the YAML an operator would have written by hand.
 *
 * Key order is left alone, so fields stay in the order the schema declares them rather than
 * being alphabetised away from it.
 */
export function toYaml(value: unknown): string {
  return stringify(withoutNulls(value), { lineWidth: 100 });
}

/**
 * Drop every object entry whose value is `null`.
 *
 * The API answers with each optional field spelled out as `null`, which fills the document
 * with lines saying nothing. An absent key reads as "unset" more clearly than `null` does,
 * and means the same thing on the way back: the server applies the field's default, which is
 * what the `null` came from.
 */
export function withoutNulls(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(withoutNulls);

  if (typeof value === "object" && value !== null) {
    return Object.fromEntries(
      Object.entries(value)
        .filter(([, entry]) => entry !== null)
        .map(([key, entry]) => [key, withoutNulls(entry)]),
    );
  }
  return value;
}
