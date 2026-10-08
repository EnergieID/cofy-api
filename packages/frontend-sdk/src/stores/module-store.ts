import { Collection } from "../core/collection.js";
import type { ModuleId, ModuleSettings } from "../types.js";

/** The modules configured per community, identified by type and name. */
export class ModuleStore extends Collection<[slug: string], ModuleSettings, ModuleId, ModuleSettings> {
  protected readonly path = "/management/communities/{slug}/modules";
  protected readonly itemPath = "/management/communities/{slug}/modules/{module_type}/{name}";

  protected idOf(module: ModuleSettings): ModuleId {
    return { type: module.type, name: module.name };
  }

  protected override idParts(id: ModuleId): unknown[] {
    return [id.type, id.name];
  }
}
