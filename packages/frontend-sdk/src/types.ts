import type { components } from "./generated/api.js";

export type CommunityInfo = components["schemas"]["CommunityInfo"];
export type CommunityBody = components["schemas"]["CommunityBody"];
export type CommunityCreate = components["schemas"]["CommunityCreate"];

/** Whether a community's API runs its saved settings: `live`, `pending` or `unavailable`. */
export type CommunityState = components["schemas"]["CommunityState"];

/** A community's state, with the revision saved and the one its API runs. */
export type CommunityStatus = components["schemas"]["CommunityStatus"];

/** What may be done to a subject: seeing it, or changing it. */
export type Action = components["schemas"]["Action"];

/** A part of a community that permissions are given on. */
export type Subject = components["schemas"]["Subject"];

/** An action on a subject of a community. */
export type Permission = components["schemas"]["Permission"];

/** What the person logged in may do in one community, or outside any one community when `slug` is `null`. */
export type CommunityPermissions = components["schemas"]["CommunityPermissions"];

/** A role granted on a community, which carries a set of permissions. */
export type Role = components["schemas"]["Role"];

/** The person logged in. */
export type Me = components["schemas"]["Me"];

/** A role on a community, granted to a person by email. */
export type GrantInfo = components["schemas"]["GrantInfo"];

/** A grant as written. */
export type GrantBody = components["schemas"]["GrantBody"];

/** One module type a community may configure, with the JSON Schema for its settings. */
export type AllowedModule = components["schemas"]["AllowedModule"];

/**
 * A module's settings as stored.
 *
 * Deliberately opaque beyond its identity: which fields a module has depends on its type,
 * and the types come from a registry the frontend does not know at build time. The schema
 * from {@link AllowedModule} is what describes the rest.
 */
export interface ModuleSettings {
  type: string;
  name: string;
  display_name?: string | null;
  description?: string | null;
  [field: string]: unknown;
}

/** Identity of a module within its community. */
export interface ModuleId {
  type: string;
  name: string;
}

/** The key a module is cached under, unique within a community. */
export function moduleKey(id: ModuleId): string {
  return `${id.type}:${id.name}`;
}

/** One resource kind a community may configure, with the JSON Schema for its settings. */
export type AllowedResource = components["schemas"]["AllowedResource"];

/** A secret as reported: everything but its value, which is never sent back. */
export type SecretInfo = components["schemas"]["SecretInfo"];

/** A secret as written: its value replaces the stored one. */
export type SecretBody = components["schemas"]["SecretBody"];

/**
 * A resource's settings as stored: a named value that modules and other resources reference.
 *
 * Opaque beyond its identity and kind, for the same reason as {@link ModuleSettings}: what a
 * resource holds depends on its kind, which {@link AllowedResource} describes.
 */
export interface ResourceSettings {
  type: string;
  name: string;
  description?: string | null;
  value?: unknown;
  [field: string]: unknown;
}

/** A reference to a resource, in place of a value. */
export interface ResourceRef {
  type: "resource";
  name: string;
}

/** What a credential field holds: a reference to one of the community's secrets. */
export interface SecretRef {
  type: "secret";
  name: string;
}

/**
 * What a field accepts a reference to, from its schema's `x-referable`: resources of `kind`,
 * holding a value of one of `types` if given.
 */
export interface Referable {
  kind: string;
  types?: readonly string[];
}
