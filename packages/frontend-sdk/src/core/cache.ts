import { StateMap } from "@dodona/lit-state";
import type { PathsWithMethod } from "openapi-typescript-helpers";

import type { ApiClient } from "../api-client.js";
import { asProblem, type ProblemError } from "../errors.js";
import type { paths } from "../generated/api.js";

/** What is cached for one scope: the last answer, the last failure, and whether it is out of date. */
interface Entry<Value> {
  value?: Value;
  error: ProblemError | null;
  stale: boolean;
}

/**
 * The answers to one GET, cached per *Scope* - the path parameters that select what is
 * fetched, `[slug]` say.
 *
 * Reading is enough to load: {@link read} answers from the cache and fetches in the background
 * when nothing is cached yet or what is cached was invalidated, so a component only renders
 * what it reads. Each scope is a key of a `StateMap`, so a fetch only re-renders the
 * components reading that scope.
 *
 * A subclass declares the {@link path} it fetches, and names {@link read} for what it caches.
 */
export abstract class Cache<Scope extends unknown[], Value> {
  protected readonly api: ApiClient;

  private readonly entries = new StateMap<string, Entry<Value>>();
  private readonly pending = new Map<string, Promise<Value>>();
  // Which request for each scope was started last, so an older answer never replaces a newer one.
  private readonly latest = new Map<string, number>();
  private started = 0;

  /** The path fetched, its `{placeholders}` filled from the scope, in order. */
  protected abstract readonly path: PathsWithMethod<paths, "get">;

  public constructor(api: ApiClient) {
    this.api = api;
  }

  /** Why the last fetch failed, or `null` when it did not. */
  public error(...scope: Scope): ProblemError | null {
    return this.entries.get(Cache.key(scope))?.error ?? null;
  }

  /** Fetch now, sharing a request that is already under way. */
  public fetch(...scope: Scope): Promise<Value> {
    const key = Cache.key(scope);
    const running = this.pending.get(key);
    if (running !== undefined) return running;

    const number = ++this.started;
    this.latest.set(key, number);
    const request: Promise<Value> = this.request(...scope).then(
      (value) => {
        this.settle(key, request, number, { value, error: null });
        return value;
      },
      (error: unknown) => {
        const problem = asProblem(error);
        this.settle(key, request, number, { value: this.entries.get(key)?.value, error: problem });
        throw problem;
      },
    );
    this.pending.set(key, request);
    return request;
  }

  /**
   * Mark the cached value as out of date.
   *
   * It stays visible, and is fetched again as soon as something reads it - right away when a
   * component is showing it, since this notifies that component.
   */
  public invalidate(...scope: Scope): void {
    const key = Cache.key(scope);
    this.pending.delete(key);
    const entry = this.entries.get(key);
    if (entry !== undefined) this.entries.set(key, { ...entry, stale: true });
  }

  /** Drop what is cached, for a scope that no longer exists. */
  public forget(...scope: Scope): void {
    const key = Cache.key(scope);
    this.pending.delete(key);
    this.latest.delete(key);
    this.entries.delete(key);
  }

  /**
   * Fetch *scope* from the API.
   *
   * What comes back is typed by the subclass's *Value*: the path is only known to be one that
   * answers a GET, not which.
   */
  protected async request(...scope: Scope): Promise<Value> {
    return (await this.api.GET(this.path, { params: { path: Cache.params(this.path, scope) } } as never)) as Value;
  }

  /** The cached value, or `undefined` until it is loaded - which reading it starts. */
  protected read(...scope: Scope): Value | undefined {
    const entry = this.entries.get(Cache.key(scope));
    // Nothing writes state before the request is answered, so this is safe during a render.
    if (entry === undefined || entry.stale) this.fetch(...scope).catch(() => {});
    return entry?.value;
  }

  /** Change a loaded value in place, with what a write returned. Does nothing when it is not loaded. */
  protected update(scope: Scope, change: (value: Value) => Value): void {
    const key = Cache.key(scope);
    const entry = this.entries.get(key);
    if (entry?.value !== undefined) this.entries.set(key, { ...entry, value: change(entry.value) });
  }

  /**
   * Store what *request* came back with.
   *
   * An answer to a request that was invalidated while under way may already be out of date, so
   * it is kept as stale - which fetches again for whoever reads it - unless a newer request was
   * started to replace it.
   */
  private settle(key: string, request: Promise<Value>, number: number, outcome: Omit<Entry<Value>, "stale">): void {
    if (this.latest.get(key) !== number) return;
    const current = this.pending.get(key) === request;
    if (current) this.pending.delete(key);
    this.entries.set(key, { ...outcome, stale: !current });
  }

  /** The path parameters of *template*, filled in the order its placeholders appear from *values*. */
  protected static params(template: string, values: readonly unknown[]): Record<string, string> {
    const names = Array.from(template.matchAll(/\{(\w+)\}/g), (match) => match[1]!);
    return Object.fromEntries(names.map((name, index) => [name, String(values[index])]));
  }

  private static key(scope: readonly unknown[]): string {
    return JSON.stringify(scope);
  }
}
