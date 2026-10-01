import { createContext } from "@lit/context";
import type {
  AllowedModulesStore,
  AllowedResourcesStore,
  CommunityStore,
  ModuleStore,
  ResourceStore,
  SecretStore,
} from "@cofy/frontend-sdk";

import type { FieldRegistry } from "./components/form/field-registry.js";
import type { CofyI18n } from "./i18n/cofy-i18n.js";
import type { ThemeState } from "./theme/theme-state.js";

/**
 * The store instances a component tree works against.
 *
 * Provided rather than imported as module singletons, so two trees on one page can point at
 * different backends - which is the difference between a library and an application's
 * globals.
 */
export const communityStoreContext = createContext<CommunityStore>(Symbol("cofy-community-store"));
export const moduleStoreContext = createContext<ModuleStore>(Symbol("cofy-module-store"));
export const allowedModulesStoreContext = createContext<AllowedModulesStore>(Symbol("cofy-allowed-modules-store"));
export const resourceStoreContext = createContext<ResourceStore>(Symbol("cofy-resource-store"));
export const secretStoreContext = createContext<SecretStore>(Symbol("cofy-secret-store"));
export const allowedResourcesStoreContext = createContext<AllowedResourcesStore>(
  Symbol("cofy-allowed-resources-store"),
);

/**
 * The community a subtree edits, provided by the editor at its root, so a field deep inside a
 * form - a reference picking one of the community's resources - knows which one to ask for.
 */
export const communitySlugContext = createContext<string>(Symbol("cofy-community-slug"));

/** The translations in effect, so every component reads one language. */
export const i18nContext = createContext<CofyI18n>(Symbol("cofy-i18n"));

/** The theme in effect, so the picker and anything previewing it agree. */
export const themeStateContext = createContext<ThemeState>(Symbol("cofy-theme-state"));

/**
 * The registry of mappers `cofy-any-form` dispatches a schema node through.
 *
 * Defaults to {@link defaultFieldRegistry} (the built-ins only), so a form works with zero
 * setup; an ancestor can `@provide` a `new FieldRegistry([...overrides])` to register its own
 * mappers ahead of the built-ins for just its subtree.
 */
export const fieldRegistryContext = createContext<FieldRegistry>(Symbol("cofy-field-registry"));
