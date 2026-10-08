import { ContextProvider } from "@lit/context";
import { ApiClient, CofyStore, type TokenInfo } from "@cofy/frontend-sdk";

import { cofyStoreContext, communitySlugContext, i18nContext } from "../../../src/context.js";
import { testI18n } from "../../support/i18n.js";

export const KEY = "cofy_generatedkey";

export interface Community {
  tokens: TokenInfo[];
  /** Every write sent, as method, path and body. */
  writes: { method: string; path: string; body: unknown }[];
}

export function community(): Community {
  return {
    tokens: [
      { name: "app", description: "Our app", expires: null },
      { name: "old", description: null, expires: "2000-01-01T00:00:00Z" },
    ],
    writes: [],
  };
}

function stubApi(state: Community): ApiClient {
  const fetchStub = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const request = input instanceof Request ? input : new Request(input, init);
    const path = new URL(request.url).pathname;
    let body: unknown = state.tokens;
    let status = 200;
    if (request.method !== "GET") {
      const sent: unknown = request.method === "DELETE" ? undefined : await request.json();
      state.writes.push({ method: request.method, path, body: sent });
      const written = sent as TokenInfo | undefined;
      body = written && {
        name: written.name,
        description: written.description ?? null,
        expires: written.expires ?? null,
        ...(request.method === "POST" ? { key: KEY } : {}),
      };
      status = request.method === "POST" ? 201 : request.method === "DELETE" ? 204 : 200;
    }
    return new Response(status === 204 ? null : JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json" },
    });
  };
  return new ApiClient({ fetch: fetchStub, baseUrl: "http://localhost" });
}

/** Mounts *element* inside the providers a page gives it: the stores, the community and the translations. */
export async function mountIn<T extends HTMLElement & { updateComplete: Promise<unknown> }>(
  element: T,
  state: Community,
): Promise<{ element: T; cofy: CofyStore }> {
  const cofy = new CofyStore(stubApi(state));
  const host = document.createElement("div");
  new ContextProvider(host, { context: cofyStoreContext, initialValue: cofy });
  new ContextProvider(host, { context: communitySlugContext, initialValue: "test" });
  new ContextProvider(host, { context: i18nContext, initialValue: await testI18n() });
  document.body.append(host);
  host.append(element);
  await settle(element);
  return { element, cofy };
}

export async function settle(element: HTMLElement & { updateComplete: Promise<unknown> }): Promise<void> {
  await element.updateComplete;
  await new Promise((resolve) => setTimeout(resolve, 10));
  await element.updateComplete;
}

/** Type into a Web Awesome control, as its own input event reports it. */
export function type(control: Element, value: string): void {
  (control as HTMLElement & { value: string }).value = value;
  control.dispatchEvent(new Event("input"));
}
