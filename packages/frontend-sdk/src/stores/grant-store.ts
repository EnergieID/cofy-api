import { Collection } from "../core/collection.js";
import type { GrantBody, GrantInfo } from "../types.js";

/** Who has access to each community, as the roles granted to them by email. */
export class GrantStore extends Collection<[slug: string], GrantInfo, string, GrantBody> {
  protected readonly path = "/management/communities/{slug}/grants";
  protected readonly itemPath = "/management/communities/{slug}/grants/{email}";

  protected idOf(grant: GrantInfo): string {
    return grant.email;
  }
}
