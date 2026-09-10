import { createContext } from "@lit/context";
import type { AllowedModulesStore, CommunityStore, ModuleStore } from "@cofy/frontend-sdk";

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
