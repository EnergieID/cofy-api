import { property } from "lit/decorators.js";
import type { JsonSchema, ValidationIssue } from "@cofy/frontend-sdk";

import { CofyElement } from "../../cofy-element.js";

/**
 * The prop contract shared by every element in the recursive form family.
 *
 * `value` is this field's own slice of the document, not the whole thing - a parent resolves
 * it once and passes it straight down. `issues` is the whole document's, unfiltered; each field
 * picks out what applies to its own pointer (or its descendants') as needed.
 */
export abstract class CofyFormField extends CofyElement {
  /** This field's own (possibly still-`$ref`'d) schema node. */
  @property({ attribute: false }) public schema: JsonSchema = {};

  /** The top-level schema, for resolving `$ref`s. */
  @property({ attribute: false }) public root: JsonSchema = {};

  /** This field's own JSON Pointer into the document. */
  @property({ type: String }) public pointer = "";

  /** This field's own current value. */
  @property({ attribute: false }) public value: unknown;

  @property({ type: Boolean }) public required = false;

  /** The whole document's issues - filter to this field's own pointer as needed. */
  @property({ attribute: false }) public issues: readonly ValidationIssue[] = [];

  /**
   * Property names this field's own object rendering should skip - not inherited by children.
   *
   * For a property already shown by whatever mounted this field (the module's own `type`, a
   * union's discriminator tag), so it does not also render a second time as an ordinary field.
   */
  @property({ attribute: false }) public hide: readonly string[] = [];

  /**
   * Render without this field's own label/card, because the ancestor that mounted it already
   * drew one - not inherited by children. Set by `cofy-union-form` on the branch it resolves
   * to, since a union's own card already contains it; a plain (non-union) nested object still
   * draws its own.
   */
  @property({ type: Boolean }) public bare = false;
}
