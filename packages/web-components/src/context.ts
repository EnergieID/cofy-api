import { createContext } from "@lit/context";
import type { AllowedModulesStore, CommunityStore, ModuleStore } from "@cofy/frontend-sdk";

import type { FieldRegistry } from "./components/form/custom-fields.js";
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

/** The translations in effect, so every component reads one language. */
export const i18nContext = createContext<CofyI18n>(Symbol("cofy-i18n"));

/** The theme in effect, so the picker and anything previewing it agree. */
export const themeStateContext = createContext<ThemeState>(Symbol("cofy-theme-state"));

/**
 * Which schema type names get a hand-written field instead of the generic form dispatch.
 *
 * Defaults to {@link defaultFieldRegistry} (nothing registered), so a form works with zero
 * setup; an ancestor can `@provide` a different registry to override it for just its subtree.
 */
export const fieldRegistryContext = createContext<FieldRegistry>(Symbol("cofy-field-registry"));
