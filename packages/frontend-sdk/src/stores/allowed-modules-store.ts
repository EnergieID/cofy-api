import { ReadonlyCollection } from "../core/collection.js";
import type { AllowedModule } from "../types.js";

/**
 * The module types each community may configure, with their schemas, identified by type.
 *
 * Never invalidated: a schema only changes when the server's installed modules do, which a
 * running page will not see.
 */
export class AllowedModulesStore extends ReadonlyCollection<[slug: string], AllowedModule, string> {
  protected readonly path = "/management/communities/{slug}/allowed-modules";

  protected idOf(allowed: AllowedModule): string {
    return allowed.type;
  }
}
