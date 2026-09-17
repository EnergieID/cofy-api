import type { components } from "./generated/api.js";

export type CommunityInfo = components["schemas"]["CommunityInfo"];
export type CommunityBody = components["schemas"]["CommunityBody"];
export type CommunityCreate = components["schemas"]["CommunityCreate"];

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
