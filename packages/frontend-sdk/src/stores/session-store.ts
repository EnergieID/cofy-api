import type { ApiClient } from "../api-client.js";
import { Cache } from "../core/cache.js";
import type { Action, Me, Subject } from "../types.js";

/**
 * Who is logged in, what they may do, and logging in and out.
 *
 * Both go through the browser, not `fetch`: the API logs in by sending the browser to the
 * identity provider and back, which leaves the session in a cookie this code never sees.
 */
export class SessionStore extends Cache<[], Me> {
  private static readonly LOGIN = "/auth/login";
  private static readonly LOGOUT = "/auth/logout";

  protected readonly path = "/auth/me";

  private readonly location: Location;

  public constructor(api: ApiClient, location: Location = window.location) {
    super(api);
    this.location = location;
  }

  /**
   * The person logged in, or `undefined` until that is known - which reading it starts.
   *
   * Without a login it stays `undefined`, with a 401 as its {@link error}: the client's
   * unauthenticated hook has already started logging in.
   */
  public get(): Me | undefined {
    return this.read();
  }

  /**
   * Whether the person logged in may do *action* to *subject* in community *slug*, or outside any
   * one community - listing or creating communities - when it is `null`.
   *
   * Only decides what to show: the API checks every request itself.
   */
  public can(action: Action, subject: Subject, slug: string | null): boolean {
    const granted = this.get()?.permissions.find((entry) => entry.slug === slug)?.permissions ?? [];
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
