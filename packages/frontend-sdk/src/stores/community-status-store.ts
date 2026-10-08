import { Cache } from "../core/cache.js";
import type { CommunityStatus } from "../types.js";

/** Whether each community's API runs its saved settings. */
export class CommunityStatusStore extends Cache<[slug: string], CommunityStatus> {
  protected readonly path = "/management/communities/{slug}/status";

  /** The status of *slug*, or `undefined` until it is loaded - which reading it starts. */
  public get(slug: string): CommunityStatus | undefined {
    return this.read(slug);
  }
}
