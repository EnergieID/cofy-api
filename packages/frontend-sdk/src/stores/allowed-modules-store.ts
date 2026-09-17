import { State, StateMap, stateProperty } from "@dodona/lit-state";

import type { ApiClient } from "../api-client.js";
import { asProblem, type ProblemError } from "../errors.js";
import type { AllowedModule } from "../types.js";

/**
 * The module types each community may configure, with their schemas.
 *
 * Cached per community without expiry: a schema only changes when the server's installed
 * modules do, which a running page will not see.
 */
export class AllowedModulesStore extends State {
  private static readonly COLLECTION = "/management/communities/{slug}/allowed-modules" as const;

  public readonly catalogs = new StateMap<string, AllowedModule[]>();

  @stateProperty public loading = false;
  @stateProperty public error: ProblemError | null = null;

  private readonly api: ApiClient;

  public constructor(api: ApiClient) {
    super();
    this.api = api;
  }

  public list(slug: string): AllowedModule[] | undefined {
    return this.catalogs.get(slug);
  }

  public find(slug: string, type: string): AllowedModule | undefined {
    return this.catalogs.get(slug)?.find((allowed) => allowed.type === type);
  }

  public async load(slug: string): Promise<void> {
    this.loading = true;
    this.error = null;
    try {
      this.catalogs.set(slug, await this.api.GET(AllowedModulesStore.COLLECTION, { params: { path: { slug } } }));
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
