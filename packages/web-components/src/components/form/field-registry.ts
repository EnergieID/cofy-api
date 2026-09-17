import type { JsonSchema } from "@cofy/frontend-sdk";

// Registers every tag `defaultFieldMappers` below names
import "./cofy-object-form.js";
import "./cofy-list-form.js";
import "./cofy-union-form.js";
import "./cofy-string-form.js";
import "./cofy-secret-form.js";
import "./cofy-number-form.js";
import "./cofy-boolean-form.js";
import "./cofy-enum-form.js";
import "./cofy-const-form.js";

import { isRecord } from "../../schema-ref.js";
import { primitiveText } from "./field-shell.js";
import { resolveNode, unionBranches } from "./schema-dispatch.js";

/**
 * One entry in a {@link FieldRegistry}.
 *
 * `matches` is checked against *node* - the field's own schema, resolved past its own `$ref`/
 * `Optional`-wrapping (see `resolveNode` in `schema-dispatch.js`). It is also what the mounted
 * tag receives as its own `.schema` - label/description travel separately, as their own props,
 * so a mapper only ever has to decide yes/no.
 *
 * `summarize`, if given, is a one-line stand-in for the full control - what a list item or a
 * collapsed details shows without mounting the real field. Optional: a mapper with nothing
 * sensible to show (a `dict[str, X]` fallback, an array) just omits it, the same as a schema no
 * mapper matches at all.
 */
export interface FieldMapper {
  matches(node: JsonSchema, root: JsonSchema): boolean;

  /** The tag to mount when this mapper matches. */
  tag: string;

  summarize?(value: unknown, node: JsonSchema, root: JsonSchema): string | undefined;
}

function readable(tag: string): string {
  return tag.replace(/_/g, " ");
}

function tagSummary(value: unknown, node: JsonSchema): string | undefined {
  if (!isRecord(value)) return undefined;
  const tag = value["type"] ?? value["kind"];
  if (typeof tag === "string") return readable(tag)
  const classname = node["title"]
  if (typeof classname == "string") return classname

  return undefined
}

/**
 * One mapper per built-in field, in the order every form dispatches through by default. Order
 * matters where a schema could fit more than one - a `secret` is also a plain `string`, so it is
 * checked first.
 */
export const defaultFieldMappers: readonly FieldMapper[] = [
  {
    tag: "cofy-union-form",
    matches: (node: JsonSchema, root: JsonSchema): boolean => unionBranches(node, root) !== undefined,
    summarize: tagSummary,
  },
  {
    tag: "cofy-enum-form",
    matches: (node: JsonSchema): boolean => Array.isArray(node["enum"]),
    summarize: primitiveText,
  },
  {
    tag: "cofy-const-form",
    matches: (node: JsonSchema): boolean => "const" in node,
    summarize: primitiveText,
  },
  {
    tag: "cofy-secret-form",
    // Never summarized - a credential has no business showing up in a collapsed header or a
    // list item, even redacted.
    matches: (node: JsonSchema): boolean =>
      node["type"] === "string" && node["format"] === "password" && node["writeOnly"] === true,
  },
  {
    tag: "cofy-string-form",
    matches: (node: JsonSchema): boolean => node["type"] === "string",
    summarize: primitiveText,
  },
  {
    tag: "cofy-number-form",
    matches: (node: JsonSchema): boolean => node["type"] === "integer" || node["type"] === "number",
    summarize: primitiveText,
  },
  {
    tag: "cofy-boolean-form",
    matches: (node: JsonSchema): boolean => node["type"] === "boolean",
    summarize: primitiveText,
  },
  {
    tag: "cofy-object-form",
    // A `dict[str, X]` schema (`additionalProperties`, no fixed `properties`) has no keys the
    // generic object renderer could draw a field for - left to the unknown-schema fallback
    // rather than silently rendering nothing.
    matches: (node: JsonSchema): boolean => node["type"] === "object" && isRecord(node["properties"]),
    summarize: tagSummary,
  },
  {
    tag: "cofy-list-form",
    matches: (node: JsonSchema): boolean => node["type"] === "array",
    summarize: (value: unknown): string | undefined => {
      if (!Array.isArray(value)) return undefined
      return value.length.toString()
    }
  },
];

/**
 * The ordered list of mappers `cofy-any-form` dispatches a schema through, tried in turn until
 * one matches - and the same list any other container asks for a tag/summary on a child it does
 * not mount itself (`cofy-list-form` for each item, `cofy-object-form`/`cofy-union-form` for
 * their own collapsed header). Provided through `fieldRegistryContext`, so a subtree can
 * register its own mappers - ahead of the built-ins, by matching the same schema shape as one of
 * them, or a shape none of them do - without every other ancestor/sibling form on the page being
 * affected.
 */
export class FieldRegistry {
  private readonly mappers: readonly FieldMapper[];

  /**
   * *overrides* are tried first - each can render/summarize a schema differently, or route it
   * to a hand-written element, before the built-ins get a chance to - and fall through to the
   * built-ins for anything they don't themselves match, so registering one custom field never
   * means also having to re-declare every ordinary one.
   */
  public constructor(overrides: readonly FieldMapper[] = []) {
    this.mappers = [...overrides, ...defaultFieldMappers];
  }

  /** The tag `cofy-any-form` should mount for *schema*, or `undefined` if nothing matches - its own `cofy-unknown-form` fallback. */
  public getTag(schema: JsonSchema, root: JsonSchema): string | undefined {
    return this.getFirstMatch(schema, root)?.mapper.tag;
  }

  /** A one-line stand-in for whatever *schema* would dispatch to, given *value* - see {@link FieldMapper.summarize}. */
  public getSummary(schema: JsonSchema, root: JsonSchema, value: unknown): string | undefined {
    const match = this.getFirstMatch(schema, root);
    return match?.mapper.summarize?.(value, match.node, root);
  }

  /** The first mapper accepting *schema* (resolved past its own `$ref`/`Optional`-wrapping), alongside that resolved node. */
  private getFirstMatch(schema: JsonSchema, root: JsonSchema): { node: JsonSchema; mapper: FieldMapper } | undefined {
    const node = resolveNode(schema, root);
    const mapper = this.mappers.find((candidate) => candidate.matches(node, root));
    return mapper === undefined ? undefined : { node, mapper };
  }
}

/** Registers nothing beyond the built-ins - every field renders through the generic dispatch. */
export const defaultFieldRegistry: FieldRegistry = new FieldRegistry();
