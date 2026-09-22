import type { JsonSchema } from "@cofy/frontend-sdk";

// Registers every tag `defaultFieldMappers` below names. A bare `import "./x.js"` would do the
// same at runtime, but this package's own build (`vite.build.config.ts`) treats each component
// file as its own entry - and a side-effect-only import between two entries with no value
// crossing the boundary is exactly the shape Rollup/Rolldown's `preserveModules` output silently
// drops, taking the mapper's element registration with it. Importing the class and storing it
// on its mapper below (`component`, otherwise unread) gives the bundler a real, externally
// observed reference it can never prove unused, instead of one it happens not to drop today.
import { CofyBooleanForm } from "./cofy-boolean-form.js";
import { CofyConstForm } from "./cofy-const-form.js";
import { CofyDictForm } from "./cofy-dict-form.js";
import { CofyEnumForm } from "./cofy-enum-form.js";
import { CofyListForm } from "./cofy-list-form.js";
import { CofyNumberForm } from "./cofy-number-form.js";
import { CofyObjectForm } from "./cofy-object-form.js";
import { CofySecretForm } from "./cofy-secret-form.js";
import { CofyStringForm } from "./cofy-string-form.js";
import { CofyUnionForm } from "./cofy-union-form.js";

import { isRecord } from "./schema/ref.js";
import { resolveNode, unionBranches } from "./schema/resolve.js";
import { arraySummary, dictSummary, primitiveText, tagSummary } from "./schema/summary.js";

export type AS_YAML_OPTION = "never" | "optional" | "default";

/**
 * One entry in a {@link FieldRegistry}.
 *
 * `matches` is checked against *node* - the field's own schema, resolved past its own `$ref`/
 * `Optional`-wrapping (see `resolveNode` in `schema/resolve.js`). It is also what the mounted
 * tag receives as its own `.schema` - label/description travel separately, as their own props,
 * so a mapper only ever has to decide yes/no.
 *
 * `summarize`, if given, is a one-line stand-in for the full control - what a list item or a
 * collapsed details shows without mounting the real field. Optional: a mapper with nothing
 * sensible to show (a secret) just omits it, the same as a schema no mapper matches at all.
 */
export interface FieldMapper {
  matches(node: JsonSchema, root: JsonSchema): boolean;

  /** The tag to mount when this mapper matches. */
  tag: string;

  /**
   * The class `tag` names, otherwise unread - `cofy-any-form` dispatches by the string alone.
   * Keeping a real reference to it here, rather than only importing it for its registration
   * side effect, is what keeps this package's own build from dropping that import - see the
   * comment on the imports above.
   */
  component: CustomElementConstructor;

  summarize?(value: unknown, node: JsonSchema, root: JsonSchema): string | undefined;

  /** Marks if an as yaml toggle should be shown in the form, or even if the yaml entry should be the default */
  asYaml?: AS_YAML_OPTION
}

/**
 * One mapper per built-in field, in the order every form dispatches through by default. Order
 * matters where a schema could fit more than one - a `secret` is also a plain `string`, so it is
 * checked first.
 */
export const defaultFieldMappers: readonly FieldMapper[] = [
  /* Special cases */
  {
    tag: "cofy-list-form",
    component: CofyListForm,
    matches: (node: JsonSchema): boolean => node["type"] === "array" && node["title"] === "Tariff",
    summarize: arraySummary,
    asYaml: "default",
  },
  /* Defaults */
  {
    tag: "cofy-union-form",
    component: CofyUnionForm,
    matches: (node: JsonSchema, root: JsonSchema): boolean => unionBranches(node, root) !== undefined,
    summarize: tagSummary,
    asYaml: "optional",
  },
  {
    tag: "cofy-enum-form",
    component: CofyEnumForm,
    matches: (node: JsonSchema): boolean => Array.isArray(node["enum"]),
    summarize: primitiveText,
  },
  {
    tag: "cofy-const-form",
    component: CofyConstForm,
    matches: (node: JsonSchema): boolean => "const" in node,
    summarize: primitiveText,
  },
  {
    tag: "cofy-secret-form",
    component: CofySecretForm,
    // Never summarized - a credential has no business showing up in a collapsed header or a
    // list item, even redacted.
    matches: (node: JsonSchema): boolean =>
      node["type"] === "string" && node["format"] === "password" && node["writeOnly"] === true,
  },
  {
    tag: "cofy-string-form",
    component: CofyStringForm,
    matches: (node: JsonSchema): boolean => node["type"] === "string",
    summarize: primitiveText,
  },
  {
    tag: "cofy-number-form",
    component: CofyNumberForm,
    matches: (node: JsonSchema): boolean => node["type"] === "integer" || node["type"] === "number",
    summarize: primitiveText,
  },
  {
    tag: "cofy-boolean-form",
    component: CofyBooleanForm,
    matches: (node: JsonSchema): boolean => node["type"] === "boolean",
    summarize: primitiveText,
  },
  {
    tag: "cofy-object-form",
    component: CofyObjectForm,
    // Requires a fixed `properties` key to draw fields for - a `dict[str, X]` schema
    // (`additionalProperties`, no `properties`) is handled by `cofy-dict-form` below instead.
    matches: (node: JsonSchema): boolean => node["type"] === "object" && isRecord(node["properties"]),
    summarize: tagSummary,
    asYaml: "optional",
  },
  {
    tag: "cofy-dict-form",
    component: CofyDictForm,
    // The opposite shape: no fixed `properties`, but a schema for every value via
    // `additionalProperties` - e.g. pydantic's `dict[str, Formula]`.
    matches: (node: JsonSchema): boolean =>
      node["type"] === "object" && !isRecord(node["properties"]) && isRecord(node["additionalProperties"]),
    summarize: dictSummary,
    asYaml: "optional",
  },
  {
    tag: "cofy-list-form",
    component: CofyListForm,
    matches: (node: JsonSchema): boolean => node["type"] === "array",
    summarize: arraySummary,
    asYaml: "optional",
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

  /** A one-line stand-in for whatever *schema* would dispatch to, given *value* - see {@link FieldMapper.summarize}. */
  public getSummary(schema: JsonSchema, root: JsonSchema, value: unknown): string | undefined {
    const node = resolveNode(schema, root);
    const match = this.getFirstMatch(node, root);
    return match?.summarize?.(value, node, root);
  }

  /** The first mapper accepting *node* - already resolved past its own `$ref`/`Optional`-wrapping (`resolveNode`), unlike `schema` in {@link getSummary}. */
  public getFirstMatch(node: JsonSchema, root: JsonSchema): FieldMapper | undefined {
    return this.mappers.find((candidate) => candidate.matches(node, root));
  }
}

/** Registers nothing beyond the built-ins - every field renders through the generic dispatch. */
export const defaultFieldRegistry: FieldRegistry = new FieldRegistry();
