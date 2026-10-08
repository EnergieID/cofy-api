import type { PathsWithMethod } from "openapi-typescript-helpers";

import type { ApiClient } from "../api-client.js";
import { withProblem } from "../errors.js";
import type { paths } from "../generated/api.js";
import { Cache } from "./cache.js";

/** A write that succeeded, for whatever depends on the collection it changed. */
export interface Change<Scope extends unknown[], Id> {
  action: "create" | "replace" | "delete";
  scope: Scope;
  id: Id;
}

/**
 * The items listed under one path, cached per *Scope* - `[slug]` for a community's modules,
 * `[]` for the communities themselves.
 *
 * Reading loads, as with any {@link Cache}: {@link all} and {@link get} return `undefined`
 * until the list has come back. A subclass declares the {@link path} it lists and the
 * {@link idOf} its items.
 */
export abstract class ReadonlyCollection<Scope extends unknown[], Item, Id> extends Cache<Scope, Item[]> {
  /** Every item in *scope*, or `undefined` until they are loaded. */
  public all(...scope: Scope): Item[] | undefined {
    return this.read(...scope);
  }

  /** The item *id* identifies, or `undefined` when it is not loaded or does not exist. */
  public get(...args: [...Scope, Id]): Item | undefined {
    const [scope, id] = ReadonlyCollection.split<Scope, Id>(args);
    return this.all(...scope)?.find((item) => this.matches(item, id));
  }

  /** The identity of *item*. */
  protected abstract idOf(item: Item): Id;

  /** The values *id* consists of, in the order an item's path takes them. By default the id itself. */
  protected idParts(id: Id): unknown[] {
    return [id];
  }

  /** Whether *item* is the one *id* identifies. */
  protected matches(item: Item, id: Id): boolean {
    return JSON.stringify(this.idParts(this.idOf(item))) === JSON.stringify(this.idParts(id));
  }

  /** Split the scope from the trailing argument after it. */
  protected static split<Scope extends unknown[], Last>(args: [...Scope, Last]): [Scope, Last] {
    return [args.slice(0, -1) as Scope, args[args.length - 1] as Last];
  }
}

/**
 * A {@link ReadonlyCollection} that can be written to, the RESTful way: a POST to its
 * {@link path} creates an item, and a PUT or DELETE to the {@link itemPath} - the same path
 * followed by the item's id - replaces or deletes one.
 *
 * A write updates the cached list from what the server returned rather than fetching it
 * again, and only when that list was loaded: caching just the written item would pass for the
 * whole list. Failures are thrown as `ProblemError`, for the caller to show.
 *
 * As with {@link Cache.request}, bodies and answers are typed by the subclass's type
 * parameters, not by the paths.
 */
export abstract class Collection<
  Scope extends unknown[],
  Item,
  Id,
  CreateBody,
  ReplaceBody = CreateBody,
> extends ReadonlyCollection<Scope, Item, Id> {
  protected abstract override readonly path: PathsWithMethod<paths, "get"> & PathsWithMethod<paths, "post">;

  /** The path of one item, its `{placeholders}` filled from the scope and then the {@link idParts}. */
  protected abstract readonly itemPath: PathsWithMethod<paths, "put"> & PathsWithMethod<paths, "delete">;

  private readonly onChange?: (change: Change<Scope, Id>) => void;

  /** *onChange* is called after every write that succeeded, to invalidate what depends on it. */
  public constructor(api: ApiClient, onChange?: (change: Change<Scope, Id>) => void) {
    super(api);
    this.onChange = onChange;
  }

  public async create(...args: [...Scope, CreateBody]): Promise<Item> {
    const [scope] = Collection.split<Scope, CreateBody>(args);
    const created = await withProblem(() => this.requestCreate(...args));
    this.update(scope, (items) => [...items, created]);
    this.onChange?.({ action: "create", scope, id: this.idOf(created) });
    return created;
  }

  public async replace(...args: [...Scope, Id, ReplaceBody]): Promise<Item> {
    const [rest] = Collection.split<[...Scope, Id], ReplaceBody>(args);
    const [scope, id] = Collection.split<Scope, Id>(rest);
    const replaced = await withProblem(() => this.requestReplace(...args));
    this.update(scope, (items) => items.map((item) => (this.matches(item, id) ? replaced : item)));
    this.onChange?.({ action: "replace", scope, id });
    return replaced;
  }

  public async delete(...args: [...Scope, Id]): Promise<void> {
    const [scope, id] = Collection.split<Scope, Id>(args);
    await withProblem(() => this.requestDelete(...args));
    this.update(scope, (items) => items.filter((item) => !this.matches(item, id)));
    this.onChange?.({ action: "delete", scope, id });
  }

  protected async requestCreate(...args: [...Scope, CreateBody]): Promise<Item> {
    const [scope, body] = Collection.split<Scope, CreateBody>(args);
    const params = Collection.params(this.path, scope);
    return (await this.api.POST(this.path, { params: { path: params }, body } as never)) as Item;
  }

  protected async requestReplace(...args: [...Scope, Id, ReplaceBody]): Promise<Item> {
    const [rest, body] = Collection.split<[...Scope, Id], ReplaceBody>(args);
    const params = this.itemParams(...rest);
    return (await this.api.PUT(this.itemPath, { params: { path: params }, body } as never)) as Item;
  }

  protected requestDelete(...args: [...Scope, Id]): Promise<void> {
    return this.api.DELETE(this.itemPath, { params: { path: this.itemParams(...args) } } as never);
  }

  private itemParams(...args: [...Scope, Id]): Record<string, string> {
    const [scope, id] = Collection.split<Scope, Id>(args);
    return Collection.params(this.itemPath, [...scope, ...this.idParts(id)]);
  }
}
