import { createContext } from "@lit/context";

import type { RouteName } from "./routes.js";
import type { CrumbState } from "./states/crumb-state.js";
import type { RouteState } from "./states/route-state.js";

/** Provided by the shell so a page can navigate and set its trail without being wired up. */
export const routeStateContext = createContext<RouteState<RouteName>>(Symbol("cofy-route-state"));
export const crumbStateContext = createContext<CrumbState>(Symbol("cofy-crumb-state"));
