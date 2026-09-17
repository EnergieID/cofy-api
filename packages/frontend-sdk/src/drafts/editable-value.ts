import { State, stateProperty } from "@dodona/lit-state";

import { validate, type JsonSchema, type ValidationIssue } from "../validation.js";

/**
 * A value being edited, checked against a schema as it changes.
 *
 * This is the part of editing that exists before a record does: no identity to save against,
 * nothing to be dirty relative to. {@link ModuleDraft} adds that once a module actually exists.
 */
export class EditableValue<T> extends State {
  @stateProperty public current: T;
  @stateProperty public issues: ValidationIssue[] = [];

  public constructor(current: T) {
    super();
    this.current = current;
  }

  public get valid(): boolean {
    return this.issues.length === 0;
  }

  public set(next: T): void {
    this.current = next;
  }

  /** Re-check the working copy, storing the result on {@link issues}. */
  public check(schema: JsonSchema): ValidationIssue[] {
    this.issues = validate(schema, this.current);
    return this.issues;
  }
}
