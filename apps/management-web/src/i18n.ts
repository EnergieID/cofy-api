/** The namespace this application's own strings live in; `components` belongs to the library. */
export const APP_NAMESPACE = "app";

/**
 * The languages this console serves, fallback first.
 *
 * A language appears here once `public/locales/<code>/app.yaml` exists. It does not need a
 * complete `components.yaml` beside it: i18next falls back key by key, so a half-finished
 * translation shows what it has and English for the rest.
 */
export const LANGUAGES = ["en", "nl"] as const;
