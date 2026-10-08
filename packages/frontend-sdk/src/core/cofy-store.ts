import type { ApiClient } from "../api-client.js";
import { AllowedModulesStore } from "../stores/allowed-modules-store.js";
import { AllowedResourcesStore } from "../stores/allowed-resources-store.js";
import { CommunityStatusStore } from "../stores/community-status-store.js";
import { CommunityStore } from "../stores/community-store.js";
import { GrantStore } from "../stores/grant-store.js";
import { ModuleStore } from "../stores/module-store.js";
import { ResourceStore } from "../stores/resource-store.js";
import { SecretStore } from "../stores/secret-store.js";
import { SessionStore } from "../stores/session-store.js";
import { TokenStore } from "../stores/token-store.js";
import type { Cache } from "./cache.js";

/**
 * Every store of the management API, against one client.
 *
 * The stores do not know of each other; what a write to one makes out of date in another is
 * decided here, in one place.
 */
export class CofyStore {
  public readonly session: SessionStore;
  public readonly communities: CommunityStore;
  public readonly status: CommunityStatusStore;
  public readonly modules: ModuleStore;
  public readonly allowedModules: AllowedModulesStore;
  public readonly resources: ResourceStore;
  public readonly allowedResources: AllowedResourcesStore;
  public readonly secrets: SecretStore;
  public readonly tokens: TokenStore;
  public readonly grants: GrantStore;

  public constructor(api: ApiClient, location: Location = window.location) {
    this.session = new SessionStore(api, location);
    this.status = new CommunityStatusStore(api);
    this.allowedModules = new AllowedModulesStore(api);
    this.allowedResources = new AllowedResourcesStore(api);

    this.communities = new CommunityStore(api, ({ action, id: slug }) => {
      // Whoever creates a community is given a role on it.
      if (action === "create") this.session.invalidate();
      if (action === "delete") this.forget(slug);
    });

    // Any change to what a community's API runs leaves that API behind until it reloads.
    this.modules = new ModuleStore(api, ({ action, scope: [slug] }) => {
      this.status.invalidate(slug);
      // The listing counts each community's modules.
      if (action !== "replace") this.communities.invalidate();
    });
    this.resources = new ResourceStore(api, ({ scope: [slug] }) => this.status.invalidate(slug));
    this.secrets = new SecretStore(api, ({ scope: [slug] }) => this.status.invalidate(slug));
    this.tokens = new TokenStore(api, ({ scope: [slug] }) => this.status.invalidate(slug));

    // A grant may be to the person logged in, which changes what they may do - and which
    // communities they may see at all. Revoking one may leave them seeing nothing of it.
    this.grants = new GrantStore(api, ({ action, scope: [slug] }) => {
      this.session.invalidate();
      if (action === "delete") {
        this.communities.invalidate();
        this.invalidate(slug);
      }
    });
  }

  /** Mark everything cached about *slug* as out of date. */
  private invalidate(slug: string): void {
    for (const store of this.perCommunity()) store.invalidate(slug);
  }

  /** Drop everything cached about *slug*, a community that no longer exists. */
  private forget(slug: string): void {
    for (const store of this.perCommunity()) store.forget(slug);
  }

  /** The stores that cache something per community. */
  private perCommunity(): Cache<[slug: string], unknown>[] {
    return [
      this.status,
      this.modules,
      this.allowedModules,
      this.resources,
      this.allowedResources,
      this.secrets,
      this.tokens,
      this.grants,
    ];
  }
}
