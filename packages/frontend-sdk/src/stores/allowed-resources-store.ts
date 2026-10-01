import { State, StateMap, stateProperty } from "@dodona/lit-state";

import type { ApiClient } from "../api-client.js";
import { asProblem, type ProblemError } from "../errors.js";
import type { AllowedResource } from "../types.js";

/**
 * The resource kinds each community may configure, with their schemas.
 *
 * Cached per community without expiry, like {@link AllowedModulesStore}.
 */
export class AllowedResourcesStore extends State {
  private static readonly COLLECTION = "/management/communities/{slug}/allowed-resources" as const;

  public readonly catalogs = new StateMap<string, AllowedResource[]>();

  @stateProperty public loading = false;
  @stateProperty public error: ProblemError | null = null;

  private readonly api: ApiClient;

  public constructor(api: ApiClient) {
    super();
    this.api = api;
  }

  public list(slug: string): AllowedResource[] | undefined {
    return this.catalogs.get(slug);
  }

  public find(slug: string, type: string): AllowedResource | undefined {
    return this.catalogs.get(slug)?.find((allowed) => allowed.type === type);
  }

  public async load(slug: string): Promise<void> {
    this.loading = true;
    this.error = null;
    try {
      this.catalogs.set(slug, await this.api.GET(AllowedResourcesStore.COLLECTION, { params: { path: { slug } } }));
    } catch (error) {
      this.error = asProblem(error);
    } finally {
      this.loading = false;
    }
  }

  public async ensure(slug: string): Promise<void> {
    if (!this.catalogs.has(slug)) await this.load(slug);
  }
}
