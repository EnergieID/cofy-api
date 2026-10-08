import { Collection } from "../core/collection.js";
import type { CreatedToken, TokenBody, TokenInfo } from "../types.js";

/** The API tokens configured per community, without their keys: those are only reported once, on creation. */
export class TokenStore extends Collection<[slug: string], TokenInfo, string, TokenBody> {
  protected readonly path = "/management/communities/{slug}/tokens";
  protected readonly itemPath = "/management/communities/{slug}/tokens/{name}";

  /** Create a token, whose generated key is in the answer but kept out of the cache. */
  public override async create(slug: string, body: TokenBody): Promise<CreatedToken> {
    // The server answers a creation with the key as well.
    const created = (await super.create(slug, body)) as CreatedToken;
    this.update([slug], (tokens) => tokens.map((token) => (token.name === created.name ? withoutKey(created) : token)));
    return created;
  }

  protected idOf(token: TokenInfo): string {
    return token.name;
  }
}

function withoutKey({ key: _, ...token }: CreatedToken): TokenInfo {
  return token;
}
