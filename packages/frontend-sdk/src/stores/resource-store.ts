import { State, StateMap, stateProperty } from "@dodona/lit-state";

import type { ApiClient } from "../api-client.js";
import { asProblem, withProblem, type ProblemError } from "../errors.js";
import type { Referable, ResourceSettings } from "../types.js";

/**
 * The resources configured per community.
 *
 * Kept like {@link ModuleStore}: one `StateMap` entry per slug, updated from what the server
 * returned rather than by reloading the list.
 */
export class ResourceStore extends State {
  private static readonly COLLECTION = "/management/communities/{slug}/resources" as const;
  private static readonly ITEM = "/management/communities/{slug}/resources/{name}" as const;

  public readonly resources = new StateMap<string, ResourceSettings[]>();

  @stateProperty public loading = false;
  @stateProperty public error: ProblemError | null = null;

  private readonly api: ApiClient;

  public constructor(api: ApiClient) {
    super();
    this.api = api;
  }

  /** Resources for *slug*, or `undefined` when they have not been loaded yet. */
  public list(slug: string): ResourceSettings[] | undefined {
    return this.resources.get(slug);
  }

  public find(slug: string, name: string): ResourceSettings | undefined {
    return this.resources.get(slug)?.find((resource) => resource.name === name);
  }

  /** Resources of *slug* a field accepting *referable* can reference, for picking one. */
  public fitting(slug: string, referable: Referable): ResourceSettings[] {
    const resources = this.resources.get(slug) ?? [];
    return resources.filter(
      (resource) => resource.type === referable.kind && this.holdsOneOf(resources, resource, referable.types),
    );
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

  public async load(slug: string): Promise<void> {
    this.loading = true;
    this.error = null;
    try {
      const resources = await this.api.GET(ResourceStore.COLLECTION, { params: { path: { slug } } });
      this.resources.set(slug, resources);
    } catch (error) {
      this.error = asProblem(error);
    } finally {
      this.loading = false;
    }
  }

  /** Load *slug*'s resources unless they are already cached. */
  public async ensure(slug: string): Promise<void> {
    if (!this.resources.has(slug)) await this.load(slug);
  }

  public async create(slug: string, resource: ResourceSettings): Promise<ResourceSettings> {
    const created = (await withProblem(() =>
      this.api.POST(ResourceStore.COLLECTION, {
        params: { path: { slug } },
        // A discriminated union the generated types spell out per kind, see `ModuleStore.create`.
        body: resource as never,
      }),
    )) as ResourceSettings;

    const cached = this.resources.get(slug);
    if (cached !== undefined) this.resources.set(slug, [...cached, created]);
    return created;
  }

  public async replace(slug: string, name: string, resource: ResourceSettings): Promise<ResourceSettings> {
    const replaced = (await withProblem(() =>
      this.api.PUT(ResourceStore.ITEM, {
        params: { path: { slug, name } },
        body: resource as never,
      }),
    )) as ResourceSettings;

    const cached = this.resources.get(slug);
    if (cached !== undefined) {
      this.resources.set(
        slug,
        cached.map((existing) => (existing.name === name ? replaced : existing)),
      );
    }
    return replaced;
  }

  public async remove(slug: string, name: string): Promise<void> {
    await withProblem(() => this.api.DELETE(ResourceStore.ITEM, { params: { path: { slug, name } } }));
    const cached = this.resources.get(slug);
    if (cached !== undefined) {
      this.resources.set(
        slug,
        cached.filter((existing) => existing.name !== name),
      );
    }
  }

  /** Drop *slug*'s cache, so the next `ensure` refetches. */
  public invalidate(slug: string): void {
    this.resources.delete(slug);
  }
}
