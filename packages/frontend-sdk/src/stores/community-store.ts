import { State, stateProperty } from "@dodona/lit-state";

import type { ApiClient } from "../api-client.js";
import { asProblem, type ProblemError } from "../errors.js";
import type { CommunityBody, CommunityCreate, CommunityInfo } from "../types.js";

/**
 * The communities this API will show, and which one is being looked at.
 *
 * The listing is the authorization seam - it answers "which communities may I see" - so the
 * set here is always whatever the server returned, never something assembled client-side.
 */
export class CommunityStore extends State {
  private static readonly COLLECTION = "/management/communities" as const;
  private static readonly ITEM = "/management/communities/{slug}" as const;

  @stateProperty public communities: CommunityInfo[] = [];
  @stateProperty public currentSlug: string | null = null;
  @stateProperty public loading = false;
  @stateProperty public loaded = false;
  @stateProperty public error: ProblemError | null = null;

  private readonly api: ApiClient;

  public constructor(api: ApiClient) {
    super();
    this.api = api;
  }

  public get current(): CommunityInfo | undefined {
    return this.communities.find((community) => community.slug === this.currentSlug);
  }

  public select(slug: string | null): void {
    this.currentSlug = slug;
  }

  public async load(): Promise<void> {
    this.loading = true;
    this.error = null;
    try {
      this.communities = await this.api.GET(CommunityStore.COLLECTION, {});
      this.loaded = true;
    } catch (error) {
      this.error = asProblem(error);
    } finally {
      this.loading = false;
    }
  }

  public async get(slug: string): Promise<CommunityInfo> {
    return await this.api.GET(CommunityStore.ITEM, { params: { path: { slug } } });
  }

  public async create(community: CommunityCreate): Promise<CommunityInfo> {
    const created = await this.api.POST(CommunityStore.COLLECTION, { body: community });
    this.communities = [...this.communities, created].sort((a, b) => a.slug.localeCompare(b.slug));
    return created;
  }

  public async update(slug: string, community: CommunityBody): Promise<CommunityInfo> {
    const updated = await this.api.PUT(CommunityStore.ITEM, { params: { path: { slug } }, body: community });
    this.communities = this.communities.map((existing) => (existing.slug === slug ? updated : existing));
    return updated;
  }

  public async remove(slug: string): Promise<void> {
    await this.api.DELETE(CommunityStore.ITEM, { params: { path: { slug } } });
    this.communities = this.communities.filter((existing) => existing.slug !== slug);
    if (this.currentSlug === slug) this.currentSlug = null;
  }
}
