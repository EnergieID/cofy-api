import { parse } from "yaml";
import type { BackendModule, ReadCallback, Services, InitOptions } from "i18next";

export interface YamlBackendOptions {
  /** Where locale files are served from. Files sit at `${basePath}/{lng}/{ns}.yaml`. */
  basePath?: string;
  /** Overridable so tests and non-browser hosts can supply their own transport. */
  fetch?: typeof globalThis.fetch;
}

/**
 * Loads translations from YAML served alongside the app.
 *
 * YAML because that is the format the rest of this project is written and reviewed in, and
 * because a translator editing one is far less likely to break it than JSON. Fetched rather
 * than bundled, so a deployment can add or correct a translation by dropping in a file
 * instead of rebuilding.
 *
 * Written here rather than pulling in `i18next-http-backend`: the whole contract is one
 * `read` method, and this way the YAML parsing has nowhere to hide.
 */
export function yamlBackend(options: YamlBackendOptions = {}): BackendModule<YamlBackendOptions> {
  const basePath = options.basePath ?? "/locales";
  const load = options.fetch ?? globalThis.fetch.bind(globalThis);

  return {
    type: "backend",
    init(_services: Services, _backendOptions: YamlBackendOptions, _i18nextOptions: InitOptions): void {
      // Nothing to set up; the options are captured above.
    },
    read(language: string, namespace: string, callback: ReadCallback): void {
      const url = `${basePath}/${language}/${namespace}.yaml`;
      load(url)
        .then(async (response) => {
          if (!response.ok) throw new Error(`${response.status} for ${url}`);
          return parse(await response.text()) as Record<string, unknown>;
        })
        // A missing or broken file must not blank the UI: i18next falls back to the next
        // language and then to the key itself, which is worse than a translation but better
        // than nothing on screen.
        .then((resources) => callback(null, resources))
        .catch((error: unknown) => callback(error as Error, false));
    },
  };
}
