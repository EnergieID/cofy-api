import { readFile } from "node:fs/promises";
import { join, resolve } from "node:path";

import { createI18n } from "../../src/i18n/i18n.js";
import type { CofyI18n } from "../../src/i18n/cofy-i18n.js";
import { yamlBackend } from "../../src/i18n/yaml-backend.js";

/**
 * An i18n instance backed by this package's real locale files, read from disk.
 *
 * Using the shipped YAML rather than a fixture means a component asking for a key that does
 * not exist fails here, instead of showing the raw key to a user.
 */
export async function testI18n(language = "en", supportedLanguages: readonly string[] = ["en"]): Promise<CofyI18n> {
  return createI18n({
    language,
    supportedLanguages,
    backend: yamlBackend({ fetch: fromDisk as unknown as typeof globalThis.fetch }),
    // A test must not inherit the language another one chose, nor leave one behind.
    storage: null,
  });
}

// Vite rewrites `import.meta.url` to a `/@fs/` path, so the root comes from the working
// directory, which vitest sets to the package being tested.
const LOCALES = resolve(process.cwd(), "locales");

async function fromDisk(url: string): Promise<Response> {
  try {
    return new Response(await readFile(join(LOCALES, url.replace("/locales/", "")), "utf8"), { status: 200 });
  } catch {
    return new Response(null, { status: 404 });
  }
}
