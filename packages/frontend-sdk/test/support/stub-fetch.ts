/** A `fetch` stand-in that records calls and replays canned responses. */
export interface Call {
  method: string;
  path: string;
  body: unknown;
  headers: Record<string, string>;
}

export interface StubResponse {
  status?: number;
  body?: unknown;
  contentType?: string;
}

export interface StubbedFetch {
  fetch: typeof globalThis.fetch;
  calls: Call[];
}

export function stubFetch(handler: (call: Call) => StubResponse | undefined): StubbedFetch {
  const calls: Call[] = [];

  const fetchStub = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const request = input instanceof Request ? input : new Request(input, init);
    const url = new URL(request.url, "http://localhost");
    const raw = await request.text();
    const call: Call = {
      method: request.method,
      path: url.pathname,
      body: raw === "" ? undefined : JSON.parse(raw),
      headers: Object.fromEntries(request.headers.entries()),
    };
    calls.push(call);

    const planned = handler(call) ?? { status: 404, body: { title: "Not Found", status: 404, detail: "no stub" } };
    const status = planned.status ?? 200;
    if (status === 204 || planned.body === undefined) {
      return new Response(null, { status });
    }
    return new Response(JSON.stringify(planned.body), {
      status,
      headers: { "content-type": planned.contentType ?? "application/json" },
    });
  };

  return { fetch: fetchStub, calls };
}
