import { stateProperty } from "@dodona/lit-state";

import type { ResourceStore } from "../stores/resource-store.js";
import type { ResourceSettings } from "../types.js";
import { EditableValue } from "./editable-value.js";

/**
 * An edit in progress of a stored resource, kept apart from it like {@link ModuleDraft}.
 *
 * A resource's identity is its name alone, which cannot change.
 */
export class ResourceDraft extends EditableValue<ResourceSettings> {
  @stateProperty public saving = false;

  /** The resource as it was when editing started. */
  public readonly original: ResourceSettings;

  /** Name to save against - taken from the original, since a rename is a different resource. */
  public readonly name: string;

  public constructor(original: ResourceSettings) {
    super(structuredClone(original));
    this.original = structuredClone(original);
    this.name = original.name;
  }

  public get dirty(): boolean {
    return JSON.stringify(this.current) !== JSON.stringify(this.original);
  }

  /** Whether saving would change the resource's name, which a replace cannot do. */
  public get renamed(): boolean {
    return this.current.name !== this.name;
  }

  public reset(): void {
    this.current = structuredClone(this.original);
    this.issues = [];
  }

  /** Write the working copy through *store*. */
  public async save(store: ResourceStore, slug: string): Promise<ResourceSettings> {
    this.saving = true;
    try {
      return await store.replace(slug, this.name, this.current);
    } finally {
      this.saving = false;
    }
  }
}
