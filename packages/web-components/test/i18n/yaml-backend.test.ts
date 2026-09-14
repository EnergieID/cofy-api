import { describe, expect, it, vi } from "vitest";

import { yamlBackend } from "../../src/i18n/yaml-backend.js";

type Read = { error: unknown; resources: unknown };

function read(backend: ReturnType<typeof yamlBackend>, language: string, namespace: string): Promise<Read> {
  return new Promise<Read>((resolve) => {
    backend.read(language, namespace, (error, resources) => resolve({ error, resources }));
  });
}

function serving(files: Record<string, string>): typeof globalThis.fetch {
  return ((url: string) =>
    Promise.resolve(
      url in files ? new Response(files[url], { status: 200 }) : new Response(null, { status: 404 }),
    )) as unknown as typeof globalThis.fetch;
}

describe("yamlBackend", () => {
  it("fetches a namespace from the path the files are served at", async () => {
    const fetch = vi.fn(serving({ "/locales/nl/components.yaml": "moduleList:\n  title: Modules\n" }));

    const { error, resources } = await read(yamlBackend({ fetch }), "nl", "components");

    expect(fetch).toHaveBeenCalledWith("/locales/nl/components.yaml");
    expect(error).toBeNull();
    expect(resources).toEqual({ moduleList: { title: "Modules" } });
  });

  it("honours a base path, for a console served under a prefix", async () => {
    const fetch = vi.fn(serving({ "/console/i18n/en/app.yaml": "title: Cofy\n" }));

    await read(yamlBackend({ basePath: "/console/i18n", fetch }), "en", "app");

    expect(fetch).toHaveBeenCalledWith("/console/i18n/en/app.yaml");
  });

  it("reports a missing file rather than throwing, so one language cannot blank the UI", async () => {
    const { error, resources } = await read(yamlBackend({ fetch: serving({}) }), "de", "components");

    expect(error).toBeInstanceOf(Error);
    expect(resources).toBe(false);
  });

  it("reports broken YAML the same way", async () => {
    const fetch = serving({ "/locales/en/components.yaml": "a:\n - b\n  c: d\n" });

    const { error } = await read(yamlBackend({ fetch }), "en", "components");

    expect(error).toBeInstanceOf(Error);
  });
});
