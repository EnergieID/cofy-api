import { State, stateProperty } from "@dodona/lit-state";

import type { ApiClient } from "../api-client.js";
import { asProblem, type ProblemError } from "../errors.js";
import type { Action, Me, Subject } from "../types.js";

/**
 * Who is logged in, what they may do, and logging in and out.
 *
 * Both go through the browser, not `fetch`: the API logs in by sending the browser to the
 * identity provider and back, which leaves the session in a cookie this code never sees.
 */
export class SessionStore extends State {
  private static readonly ME = "/auth/me" as const;
  private static readonly LOGIN = "/auth/login";
  private static readonly LOGOUT = "/auth/logout";

  @stateProperty public me: Me | null = null;
  @stateProperty public loaded = false;
  @stateProperty public error: ProblemError | null = null;

  private readonly api: ApiClient;
  private readonly location: Location;

  public constructor(api: ApiClient, location: Location = window.location) {
    super();
    this.api = api;
    this.location = location;
  }

  public async load(): Promise<void> {
    this.error = null;
    try {
      this.me = await this.api.GET(SessionStore.ME, {});
      this.loaded = true;
    } catch (error) {
      // Without a login, the client's unauthenticated hook has already started one.
      this.error = asProblem(error);
    }
  }

  /**
   * Whether the person logged in may do *action* to *subject* in community *slug*, or outside any
   * one community - listing or creating communities - when it is `null`.
   *
   * Only decides what to show: the API checks every request itself.
   */
  public can(action: Action, subject: Subject, slug: string | null): boolean {
    const granted = this.me?.permissions.find((entry) => entry.slug === slug)?.permissions ?? [];
    return granted.some((permission) => permission.action === action && permission.subject === subject);
  }

  /** Log in, coming back to the page shown now. */
  public login(): void {
    const returnTo = this.location.pathname + this.location.search + this.location.hash;
    this.location.assign(`${SessionStore.LOGIN}?return_to=${encodeURIComponent(returnTo)}`);
  }

  /** Log out here and at the identity provider. */
  public logout(): void {
    // A form, because logging out is a POST the browser itself has to follow the redirect of.
    const form = document.createElement("form");
    form.method = "POST";
    form.action = SessionStore.LOGOUT;
    document.body.append(form);
    form.submit();
  }
}
