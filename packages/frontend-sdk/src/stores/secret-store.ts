import { Collection } from "../core/collection.js";
import type { SecretBody, SecretInfo } from "../types.js";

/** The secrets configured per community, without their values: those are only ever written. */
export class SecretStore extends Collection<[slug: string], SecretInfo, string, SecretBody> {
  protected readonly path = "/management/communities/{slug}/secrets";
  protected readonly itemPath = "/management/communities/{slug}/secrets/{name}";

  protected idOf(secret: SecretInfo): string {
    return secret.name;
  }
}
