import { State, StateMap, stateProperty } from "@dodona/lit-state";

import type { ApiClient } from "../api-client.js";
import { asProblem, withProblem, type ProblemError } from "../errors.js";
import type { SecretBody, SecretInfo } from "../types.js";

/**
 * The secrets configured per community, without their values: those are only ever written.
 *
 * Kept like {@link ResourceStore}: one `StateMap` entry per slug, updated from what the server
 * returned rather than by reloading the list.
 */
export class SecretStore extends State {
  private static readonly COLLECTION = "/management/communities/{slug}/secrets" as const;
  private static readonly ITEM = "/management/communities/{slug}/secrets/{name}" as const;

  public readonly secrets = new StateMap<string, SecretInfo[]>();

  @stateProperty public loading = false;
  @stateProperty public error: ProblemError | null = null;

  private readonly api: ApiClient;

  public constructor(api: ApiClient) {
    super();
    this.api = api;
  }

  /** Secrets for *slug*, or `undefined` when they have not been loaded yet. */
  public list(slug: string): SecretInfo[] | undefined {
    return this.secrets.get(slug);
  }

  public find(slug: string, name: string): SecretInfo | undefined {
    return this.secrets.get(slug)?.find((secret) => secret.name === name);
  }

  public async load(slug: string): Promise<void> {
    this.loading = true;
    this.error = null;
    try {
      this.secrets.set(slug, await this.api.GET(SecretStore.COLLECTION, { params: { path: { slug } } }));
    } catch (error) {
      this.error = asProblem(error);
    } finally {
      this.loading = false;
    }
  }

  /** Load *slug*'s secrets unless they are already cached. */
  public async ensure(slug: string): Promise<void> {
    if (!this.secrets.has(slug)) await this.load(slug);
  }

  public async create(slug: string, secret: SecretBody): Promise<SecretInfo> {
    const created = await withProblem(() =>
      this.api.POST(SecretStore.COLLECTION, { params: { path: { slug } }, body: secret }),
    );

    const cached = this.secrets.get(slug);
    if (cached !== undefined) this.secrets.set(slug, [...cached, created]);
    return created;
  }

  /** Overwrite *name*'s value and description. */
  public async replace(slug: string, name: string, secret: SecretBody): Promise<SecretInfo> {
    const replaced = await withProblem(() =>
      this.api.PUT(SecretStore.ITEM, { params: { path: { slug, name } }, body: secret }),
    );

    const cached = this.secrets.get(slug);
    if (cached !== undefined) {
      this.secrets.set(
        slug,
        cached.map((existing) => (existing.name === name ? replaced : existing)),
      );
    }
    return replaced;
  }

  public async remove(slug: string, name: string): Promise<void> {
    await withProblem(() => this.api.DELETE(SecretStore.ITEM, { params: { path: { slug, name } } }));
    const cached = this.secrets.get(slug);
    if (cached !== undefined) {
      this.secrets.set(
        slug,
        cached.filter((existing) => existing.name !== name),
      );
    }
  }
}
