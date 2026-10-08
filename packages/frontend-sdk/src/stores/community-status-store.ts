import { State, StateMap, stateProperty } from "@dodona/lit-state";

import type { ApiClient } from "../api-client.js";
import { asProblem, type ProblemError } from "../errors.js";
import type { CommunityStatus } from "../types.js";

/** Whether each community's API runs its saved settings, one `StateMap` entry per slug. */
export class CommunityStatusStore extends State {
  private static readonly ITEM = "/management/communities/{slug}/status" as const;

  public readonly statuses = new StateMap<string, CommunityStatus>();

  @stateProperty public error: ProblemError | null = null;

  private readonly api: ApiClient;

  public constructor(api: ApiClient) {
    super();
    this.api = api;
  }

  /** The status of *slug*, or `undefined` when it has not been loaded yet. */
  public status(slug: string): CommunityStatus | undefined {
    return this.statuses.get(slug);
  }

  public async load(slug: string): Promise<void> {
    this.error = null;
    try {
      this.statuses.set(slug, await this.api.GET(CommunityStatusStore.ITEM, { params: { path: { slug } } }));
    } catch (error) {
      // An earlier answer would be shown as if it still held.
      this.statuses.delete(slug);
      this.error = asProblem(error);
    }
  }
}
