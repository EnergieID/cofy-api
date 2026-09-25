import { ApiClient } from "../../src/api-client.js";
import { stubFetch, type Call, type StubResponse } from "./stub-fetch.js";

/** The browser default of "/" resolves against the page; Node has no origin to resolve
 * against, so tests name one explicitly. */
export const ORIGIN = "http://localhost";

export interface StubbedApi {
  api: ApiClient;
  calls: Call[];
}

/** A client whose transport answers with whatever *handler* returns, recording every call. */
export function stubbedApi(handler: (call: Call) => StubResponse | undefined): StubbedApi {
  const { fetch, calls } = stubFetch(handler);
  return { api: new ApiClient({ fetch, baseUrl: ORIGIN }), calls };
}

/** A client whose transport always throws, the way a genuine network failure would - never
 * a `ProblemError`, since that only exists once a response has actually come back. */
export function failingApi(): ApiClient {
  const fetch: typeof globalThis.fetch = (): Promise<Response> => Promise.reject(new TypeError("network error"));
  return new ApiClient({ fetch, baseUrl: ORIGIN });
}
