import type { TemplateResult } from "lit";

/** The values a path's `:name` segments captured. */
export type RouteParams = Record<string, string>;

/**
 * One route.
 *
 * The shape follows `@lit-labs/router`'s route config: a path pattern, and a render function
 * taking the captured parameters.
 */
export interface RouteDefinition {
  /** A pattern such as `/c/:slug/:type/:name`. Segments starting with `:` capture. */
  path: string;
  render: (params: RouteParams) => TemplateResult;
}

/** A set of routes, keyed by name. */
export type RouteTable<Name extends string = string> = Record<Name, RouteDefinition>;

export interface RouteMatch<Name extends string = string> {
  name: Name;
  route: RouteDefinition;
  params: RouteParams;
}

/**
 * The first route in *routes* whose pattern matches *path*.
 *
 * Matching is by declaration order, so a pattern with a literal segment has to be declared
 * before one whose parameter would also match it.
 */
export function matchRoute<Name extends string>(
  routes: RouteTable<Name>,
  path: string,
): RouteMatch<Name> | undefined {
  const segments = split(path);

  for (const [name, route] of Object.entries<RouteDefinition>(routes)) {
    const params = matchPattern(route.path, segments);
    if (params !== undefined) return { name: name as Name, route, params };
  }
  return undefined;
}

/** Fill a pattern's parameters, e.g. `/c/:slug` with `{slug: "foo"}` gives `/c/foo`. */
export function buildPath(pattern: string, params: RouteParams = {}): string {
  const filled = split(pattern).map((segment) => {
    if (!segment.startsWith(":")) return segment;

    const value = params[segment.slice(1)];
    if (value === undefined) throw new Error(`Missing route parameter ${segment} for ${pattern}`);
    return encodeURIComponent(value);
  });
  return `/${filled.join("/")}`;
}

/** The same, as the hash a link or `window.location` wants. */
export function buildHash(pattern: string, params: RouteParams = {}): string {
  return `#${buildPath(pattern, params)}`;
}

/** The path a hash addresses, e.g. `#/c/foo` gives `/c/foo`. */
export function pathFromHash(hash: string): string {
  const path = hash.replace(/^#/, "");
  return path === "" ? "/" : path;
}

function matchPattern(pattern: string, segments: string[]): RouteParams | undefined {
  const expected = split(pattern);
  if (expected.length !== segments.length) return undefined;

  const params: RouteParams = {};
  for (const [index, part] of expected.entries()) {
    const actual = segments[index]!;
    if (part.startsWith(":")) params[part.slice(1)] = decodeURIComponent(actual);
    else if (part !== actual) return undefined;
  }
  return params;
}

function split(path: string): string[] {
  return path.split("/").filter((segment) => segment !== "");
}
