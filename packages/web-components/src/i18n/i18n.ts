import i18next, { type BackendModule, type InitOptions } from "i18next";

import { CofyI18n } from "./cofy-i18n.js";

/** The namespace this package's own strings live in. */
export const COMPONENTS_NAMESPACE = "components";

export interface I18nOptions {
  /** Starting language. Defaults to the browser's, narrowed to one we serve. */
  language?: string;
  /** Languages this deployment serves. The first is the fallback. */
  supportedLanguages?: readonly string[];
  /** Namespaces to load. This package's own is always included. */
  namespaces?: readonly string[];
  /**
   * How translations are loaded.
   *
   * Not assumed: a caller supplying `init.resources` directly needs none of this, and one
   * fetching from a backend picks whichever i18next `BackendModule` fits - `yamlBackend`,
   * ships alongside this function for that, `i18next-http-backend`, or one of their own.
   */
  backend?: BackendModule;
  /** Escape hatch for anything else i18next takes, including `resources` for dict-based use. */
  init?: InitOptions;
  /** Where the chosen language is remembered. Defaults to `localStorage`; `null` to not remember. */
  storage?: Pick<Storage, "getItem" | "setItem"> | null;
}

const STORAGE_KEY = "cofy.language";

/**
 * Build an i18next instance for a console, as lit-state.
 *
 * A fresh instance rather than i18next's global one, so it can be handed down through context
 * like the stores are - two consoles on a page keep their own language, and a test does not
 * inherit another test's.
 *
 * Namespaces are what make this usable from a library: this package ships `components`, an
 * application adds its own, and a deployment overrides individual keys by supplying its own
 * resources. Fallback is per key, not per file, so a half-finished translation shows what it
 * has and English for the rest.
 *
 * Resolves once the starting language has loaded.
 */
export async function createI18n(options: I18nOptions = {}): Promise<CofyI18n> {
  const supported = options.supportedLanguages ?? ["en"];
  const namespaces = [...new Set([COMPONENTS_NAMESPACE, ...(options.namespaces ?? [])])];

  const storage = options.storage === undefined ? safeLocalStorage() : options.storage;
  const remembered = storage?.getItem(STORAGE_KEY);

  const instance = i18next.createInstance();
  if (options.backend !== undefined) instance.use(options.backend);

  // Awaited rather than left running: a backend fetches, and a caller that rendered before it
  // resolved would put raw keys on screen.
  await instance.init({
    lng: options.language ?? pick(remembered, supported) ?? preferredLanguage(supported),
    fallbackLng: supported[0],
    supportedLngs: [...supported],
    ns: namespaces,
    defaultNS: COMPONENTS_NAMESPACE,
    interpolation: {
      // Values come from our own code and the API, and Lit escapes what it renders.
      escapeValue: false,
    },
    ...options.init,
  });

  // Remembered here rather than in the picker, so any route to a language change - a picker,
  // a deep link, an embedding app - is persisted the same way.
  instance.on("languageChanged", (language: string) => storage?.setItem(STORAGE_KEY, language));

  return new CofyI18n(instance);
}

/** *language*, if this deployment still serves it - a remembered one may have been dropped. */
function pick(language: string | null | undefined, supported: readonly string[]): string | undefined {
  return language !== null && language !== undefined && supported.includes(language) ? language : undefined;
}

/** `localStorage` throws rather than returning null in a blocked-cookies context. */
function safeLocalStorage(): Pick<Storage, "getItem" | "setItem"> | null {
  try {
    globalThis.localStorage.getItem(STORAGE_KEY);
    return globalThis.localStorage;
  } catch {
    return null;
  }
}

/** The first language the browser asks for that this deployment actually serves. */
export function preferredLanguage(supported: readonly string[]): string {
  for (const candidate of globalThis.navigator?.languages ?? []) {
    const base = candidate.split("-")[0]!;
    const match = supported.find((language) => language === candidate || language === base);
    if (match !== undefined) return match;
  }
  return supported[0] ?? "en";
}
