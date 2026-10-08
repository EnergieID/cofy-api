import { Collection } from "../core/collection.js";
import type { Referable, ResourceSettings } from "../types.js";

/** The resources configured per community. */
export class ResourceStore extends Collection<[slug: string], ResourceSettings, string, ResourceSettings> {
  protected readonly path = "/management/communities/{slug}/resources";
  protected readonly itemPath = "/management/communities/{slug}/resources/{name}";

  /** Resources of *slug* a field accepting *referable* can reference, for picking one. */
  public fitting(slug: string, referable: Referable): ResourceSettings[] {
    const resources = this.all(slug) ?? [];
    return resources.filter(
      (resource) => resource.type === referable.kind && this.holdsOneOf(resources, resource, referable.types),
    );
  }

  protected idOf(resource: ResourceSettings): string {
    return resource.name;
  }

  /** Whether *resource* holds a value of one of *types*, following resources that reference another. */
  private holdsOneOf(
    resources: readonly ResourceSettings[],
    resource: ResourceSettings,
    types: readonly string[] | undefined,
  ): boolean {
    if (types === undefined) return true;
    const seen = new Set<string>();
    let current: ResourceSettings | undefined = resource;
    while (current !== undefined && !seen.has(current.name)) {
      seen.add(current.name);
      const value = current.value as { type?: unknown; name?: unknown } | undefined;
      if (value?.type !== "resource") return typeof value?.type === "string" && types.includes(value.type);
      current = resources.find((candidate) => candidate.name === value.name);
    }
    return false;
  }
}
