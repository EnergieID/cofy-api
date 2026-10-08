import { ReadonlyCollection } from "../core/collection.js";
import type { AllowedResource } from "../types.js";

/** The resource kinds each community may configure, with their schemas, like {@link AllowedModulesStore}. */
export class AllowedResourcesStore extends ReadonlyCollection<[slug: string], AllowedResource, string> {
  protected readonly path = "/management/communities/{slug}/allowed-resources";

  protected idOf(allowed: AllowedResource): string {
    return allowed.type;
  }
}
