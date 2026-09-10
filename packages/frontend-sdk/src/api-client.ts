import createClient from "openapi-fetch";
import type { Client, MaybeOptionalInit, MethodResponse } from "openapi-fetch";
import type { PathsWithMethod, RequiredKeysOf } from "openapi-typescript-helpers";

import { ProblemError } from "./errors.js";
import type { paths } from "./generated/api.js";

export interface ApiClientOptions {
  /** Where the management API lives. Defaults to the page's own origin. */
  baseUrl?: string;
  /** Sent with every request; the seam auth will use. */
  headers?: Record<string, string>;
  /** Overridable so tests and non-browser hosts can supply their own transport. */
  fetch?: typeof globalThis.fetch;
}

/**
 * How `openapi-fetch` takes its per-request options: omittable when nothing is required for
 * that path, mandatory when parameters or a body are. Mirrored here rather than imported
 * because `openapi-fetch` does not export it.
 */
type InitParam<Init> =
  RequiredKeysOf<Init> extends never
    ? [(Init & { [key: string]: unknown })?]
    : [Init & { [key: string]: unknown }];

/** The options accepted for *Method* on *Path*. */
type Init<Method extends "get" | "post" | "put" | "delete", Path extends PathsWithMethod<paths, Method>> = InitParam<
  MaybeOptionalInit<paths[Path], Method>
>;

/** The body of a successful response to *Method* on *Path*. */
type Body<
  Method extends "get" | "post" | "put" | "delete",
  Path extends PathsWithMethod<paths, Method>,
> = MethodResponse<Client<paths>, Method, Path>;

/**
 * The management API, typed from its OpenAPI document.
 *
 * `openapi-fetch` resolves with `{ data, error, response }` and leaves the caller to sort out
 * which arrived. Since every caller here wants the body and treats a failure as exceptional,
 * that is done once: each method resolves with the response body, or throws
 * {@link ProblemError} carrying the problem document the API returned.
 *
 * Paths, parameters and bodies keep their generated types, so a wrong path, a missing
 * parameter or a mistyped field is still a compile error.
 */
export class ApiClient {
  private readonly client: Client<paths>;

  public constructor(options: ApiClientOptions = {}) {
    this.client = createClient<paths>({
      baseUrl: options.baseUrl ?? "/",
      headers: options.headers,
      fetch: options.fetch,
    });
  }

  public async GET<Path extends PathsWithMethod<paths, "get">>(
    path: Path,
    ...init: Init<"get", Path>
  ): Promise<Body<"get", Path>> {
    return this.body(await this.client.GET(path, ...init));
  }

  public async POST<Path extends PathsWithMethod<paths, "post">>(
    path: Path,
    ...init: Init<"post", Path>
  ): Promise<Body<"post", Path>> {
    return this.body(await this.client.POST(path, ...init));
  }

  public async PUT<Path extends PathsWithMethod<paths, "put">>(
    path: Path,
    ...init: Init<"put", Path>
  ): Promise<Body<"put", Path>> {
    return this.body(await this.client.PUT(path, ...init));
  }

  /** This API's deletes answer 204, so there is no body to return. */
  public async DELETE<Path extends PathsWithMethod<paths, "delete">>(
    path: Path,
    ...init: Init<"delete", Path>
  ): Promise<void> {
    this.check(await this.client.DELETE(path, ...init));
  }

  /**
   * The body of a successful response.
   *
   * `data` is optional on the result type because a failure carries `error` instead; the
   * check rules that out, which is what makes the assertion sound. It lives here so no call
   * site has to repeat it.
   */
  private body<T>(result: { data?: unknown; error?: unknown; response: Response }): T {
    this.check(result);
    return result.data as T;
  }

  private check(result: { error?: unknown; response: Response }): void {
    if (!result.response.ok) {
      throw ProblemError.from(result.response.status, result.error);
    }
  }
}
