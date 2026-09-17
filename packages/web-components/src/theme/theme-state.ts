import { State, stateProperty } from "@dodona/lit-state";

/** What the reader chose. "system" defers to the operating system, and keeps deferring. */
export type ColorScheme = "system" | "light" | "dark";

/** The choices a picker offers, in order. */
export const COLOR_SCHEMES = ["system", "light", "dark"] as const;

export interface ThemeOptions {
  /** Where the classes are applied. Defaults to the document. */
  target?: Document;
  /** Where the choice is remembered. Defaults to `localStorage`; pass `null` to not remember. */
  storage?: Pick<Storage, "getItem" | "setItem"> | null;
  /** The system preference to follow. Injectable so a test can drive it. */
  media?: MediaQueryList | null;
}

const STORAGE_KEY = "cofy.theme";

function isColorScheme(value: unknown): value is ColorScheme {
  return typeof value === "string" && (COLOR_SCHEMES as readonly string[]).includes(value);
}

/**
 * The colour scheme in effect, for the whole page.
 *
 * Web Awesome ships both schemes in its theme and switches on a `wa-light` or `wa-dark` class
 * at the root, but deliberately does not detect the system preference itself - it leaves that
 * to the application, which is what this is. Because the classes sit on the document and
 * custom properties inherit through shadow roots, one class reaches every component, the code
 * editor included.
 *
 * Deliberately global. Theming a subtree is possible with the same classes on a container, but
 * nothing here needs it and supporting both would cost more than it is worth.
 */
export class ThemeState extends State {
  @stateProperty public scheme: ColorScheme = "system";

  /**
   * Whether the system currently asks for dark.
   *
   * Reactive on purpose: while the scheme is "system" the OS can flip without `scheme`
   * changing, so without this nothing reading {@link resolved} would be told to re-render.
   */
  @stateProperty private systemDark = false;

  private readonly target: Document;
  private readonly storage: Pick<Storage, "getItem" | "setItem"> | null;
  private readonly media: MediaQueryList | null;

  public constructor(options: ThemeOptions = {}) {
    super();
    this.target = options.target ?? document;
    this.storage = options.storage === undefined ? safeLocalStorage() : options.storage;
    this.media =
      options.media === undefined ? (globalThis.matchMedia?.("(prefers-color-scheme: dark)") ?? null) : options.media;
    this.systemDark = this.media?.matches ?? false;
    this.scheme = this.remembered() ?? "system";
  }

  /** Apply the scheme and start following the system preference. */
  public start(): void {
    this.media?.addEventListener("change", this.onSystemChange);
    this.apply();
  }

  /** Stop following the system preference, so a torn-down console leaves no listener behind. */
  public stop(): void {
    this.media?.removeEventListener("change", this.onSystemChange);
  }

  public select(scheme: ColorScheme): void {
    if (scheme === this.scheme) return;
    this.scheme = scheme;
    this.storage?.setItem(STORAGE_KEY, scheme);
    this.apply();
  }

  /** The scheme actually on screen, which for "system" is whatever the OS currently asks for. */
  public get resolved(): "light" | "dark" {
    if (this.scheme === "system") return this.systemDark ? "dark" : "light";
    return this.scheme;
  }

  public get isDark(): boolean {
    return this.resolved === "dark";
  }

  private apply(): void {
    const root = this.target.documentElement;
    const dark = this.isDark;
    root.classList.toggle("wa-dark", dark);
    root.classList.toggle("wa-light", !dark);
  }

  private readonly onSystemChange = (event: MediaQueryListEvent): void => {
    this.systemDark = event.matches;
    // An explicit choice outranks the system, so only "system" repaints here.
    if (this.scheme === "system") this.apply();
  };

  private remembered(): ColorScheme | undefined {
    const stored = this.storage?.getItem(STORAGE_KEY);
    return isColorScheme(stored) ? stored : undefined;
  }
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
