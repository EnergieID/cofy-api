import { ContextProvider } from "@lit/context";
import { ApiClient, GrantStore, type GrantInfo } from "@cofy/frontend-sdk";

import { communitySlugContext, grantStoreContext, i18nContext } from "../../../src/context.js";
import { testI18n } from "../../support/i18n.js";

export interface Community {
  grants: GrantInfo[];
  /** Every write sent, as method, path and body. */
  writes: { method: string; path: string; body: unknown }[];
}

export function community(): Community {
  return {
    grants: [
      { email: "ann@example.com", role: "community_admin", bound: true },
      { email: "bob@example.com", role: "community_admin", bound: false },
    ],
    writes: [],
  };
}

function stubApi(state: Community): ApiClient {
  const fetchStub = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const request = input instanceof Request ? input : new Request(input, init);
    const path = decodeURIComponent(new URL(request.url).pathname);
    let body: unknown = state.grants;
    let status = 200;
    if (request.method !== "GET") {
      const sent: unknown = request.method === "DELETE" ? undefined : await request.json();
      state.writes.push({ method: request.method, path, body: sent });
      body = sent === undefined ? undefined : { ...(sent as object), bound: false };
      status = request.method === "POST" ? 201 : request.method === "DELETE" ? 204 : 200;
    }
    return new Response(status === 204 ? null : JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json" },
    });
  };
  return new ApiClient({ fetch: fetchStub, baseUrl: "http://localhost" });
}

/** Mounts *element* inside the providers a community page gives it. */
export async function mountIn<T extends HTMLElement & { updateComplete: Promise<unknown> }>(
  element: T,
  state: Community,
): Promise<T> {
  const host = document.createElement("div");
  new ContextProvider(host, { context: grantStoreContext, initialValue: new GrantStore(stubApi(state)) });
  new ContextProvider(host, { context: communitySlugContext, initialValue: "test" });
  new ContextProvider(host, { context: i18nContext, initialValue: await testI18n() });
  document.body.append(host);
  host.append(element);
  await settle(element);
  return element;
}

export async function settle(element: HTMLElement & { updateComplete: Promise<unknown> }): Promise<void> {
  await element.updateComplete;
  await new Promise((resolve) => setTimeout(resolve, 10));
  await element.updateComplete;
}
