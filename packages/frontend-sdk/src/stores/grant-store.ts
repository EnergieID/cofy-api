import { State, StateMap, stateProperty } from "@dodona/lit-state";

import type { ApiClient } from "../api-client.js";
import { asProblem, withProblem, type ProblemError } from "../errors.js";
import type { GrantBody, GrantInfo } from "../types.js";

/**
 * Who has access to each community, as the roles granted to them by email.
 *
 * Kept like {@link SecretStore}: one `StateMap` entry per slug, updated from what the server
 * returned rather than by reloading the list.
 */
export class GrantStore extends State {
  private static readonly COLLECTION = "/management/communities/{slug}/grants" as const;
  private static readonly ITEM = "/management/communities/{slug}/grants/{email}" as const;

  public readonly grants = new StateMap<string, GrantInfo[]>();

  @stateProperty public loading = false;
  @stateProperty public error: ProblemError | null = null;

  private readonly api: ApiClient;

  public constructor(api: ApiClient) {
    super();
    this.api = api;
  }

  /** Grants on *slug*, or `undefined` when they have not been loaded yet. */
  public list(slug: string): GrantInfo[] | undefined {
    return this.grants.get(slug);
  }

  public find(slug: string, email: string): GrantInfo | undefined {
    return this.grants.get(slug)?.find((grant) => grant.email === email);
  }

  public async load(slug: string): Promise<void> {
    this.loading = true;
    this.error = null;
    try {
      this.grants.set(slug, await this.api.GET(GrantStore.COLLECTION, { params: { path: { slug } } }));
    } catch (error) {
      this.error = asProblem(error);
    } finally {
      this.loading = false;
    }
  }

  /** Load *slug*'s grants unless they are already cached. */
  public async ensure(slug: string): Promise<void> {
    if (!this.grants.has(slug)) await this.load(slug);
  }

  public async create(slug: string, grant: GrantBody): Promise<GrantInfo> {
    const created = await withProblem(() =>
      this.api.POST(GrantStore.COLLECTION, { params: { path: { slug } }, body: grant }),
    );

    const cached = this.grants.get(slug);
    if (cached !== undefined) this.grants.set(slug, [...cached, created]);
    return created;
  }

  /** Change the role granted to *email*. */
  public async replace(slug: string, email: string, grant: GrantBody): Promise<GrantInfo> {
    const replaced = await withProblem(() =>
      this.api.PUT(GrantStore.ITEM, { params: { path: { slug, email } }, body: grant }),
    );

    const cached = this.grants.get(slug);
    if (cached !== undefined) {
      this.grants.set(
        slug,
        cached.map((existing) => (existing.email === email ? replaced : existing)),
      );
    }
    return replaced;
  }

  public async remove(slug: string, email: string): Promise<void> {
    await withProblem(() => this.api.DELETE(GrantStore.ITEM, { params: { path: { slug, email } } }));
    const cached = this.grants.get(slug);
    if (cached !== undefined) {
      this.grants.set(
        slug,
        cached.filter((existing) => existing.email !== email),
      );
    }
  }
}
