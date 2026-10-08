import { Collection } from "../core/collection.js";
import type { CommunityBody, CommunityCreate, CommunityInfo } from "../types.js";

/**
 * The communities this API will show.
 *
 * The listing is the authorization seam - it answers "which communities may I see" - so the
 * set here is always whatever the server returned, never something assembled client-side.
 */
export class CommunityStore extends Collection<[], CommunityInfo, string, CommunityCreate, CommunityBody> {
  protected readonly path = "/management/communities";
  protected readonly itemPath = "/management/communities/{slug}";

  protected idOf(community: CommunityInfo): string {
    return community.slug;
  }
}
