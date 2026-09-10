import { State, stateProperty } from "@dodona/lit-state";

import type { ModuleStore } from "../stores/module-store.js";
import { moduleKey, type ModuleId, type ModuleSettings } from "../types.js";
import { validate, type JsonSchema, type ValidationIssue } from "../validation.js";

/**
 * An edit in progress, kept apart from the stored module it came from.
 *
 * A write to this API is a full replace, so the payload is the whole module. Holding the
 * original alongside the working copy is what makes it possible to tell whether anything
 * changed, to discard an edit, and to leave the store's cache untouched until a save
 * actually succeeds.
 */
export class ModuleDraft extends State {
  @stateProperty public current: ModuleSettings;
  @stateProperty public issues: ValidationIssue[] = [];
  @stateProperty public saving = false;

  /** The module as it was when editing started. */
  public readonly original: ModuleSettings;

  /** Identity to save against - taken from the original, since a rename is a different module. */
  public readonly id: ModuleId;

  public constructor(original: ModuleSettings) {
    super();
    this.original = structuredClone(original);
    this.current = structuredClone(original);
    this.id = { type: original.type, name: original.name };
  }

  public get dirty(): boolean {
    return JSON.stringify(this.current) !== JSON.stringify(this.original);
  }

  public get valid(): boolean {
    return this.issues.length === 0;
  }

  /** Whether saving would change the module's identity, which a replace cannot do. */
  public get renamed(): boolean {
    return moduleKey(this.current) !== moduleKey(this.id);
  }

  public set(next: ModuleSettings): void {
    this.current = next;
  }

  public reset(): void {
    this.current = structuredClone(this.original);
    this.issues = [];
  }

  /** Re-check the working copy, storing the result on {@link issues}. */
  public check(schema: JsonSchema): ValidationIssue[] {
    this.issues = validate(schema, this.current);
    return this.issues;
  }

  /**
   * Write the working copy through *store*.
   *
   * The saved module becomes the new original, so a second save from the same editor starts
   * from what the server actually stored rather than from what was first opened.
   */
  public async save(store: ModuleStore, slug: string): Promise<ModuleSettings> {
    this.saving = true;
    try {
      const saved = await store.replace(slug, this.id, this.current);
      return saved;
    } finally {
      this.saving = false;
    }
  }
}
