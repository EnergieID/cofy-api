import { State, StateMap, stateProperty } from "@dodona/lit-state";

import type { ApiClient } from "../api-client.js";
import { asProblem, type ProblemError } from "../errors.js";
import { moduleKey, type ModuleId, type ModuleSettings } from "../types.js";

/**
 * The modules configured per community.
 *
 * Held in a `StateMap` keyed by slug, so a write for one community only notifies the
 * components reading that community - and updating it does not mean rebuilding a record of
 * every community that was ever loaded.
 *
 * A write updates the cached entry from what the server returned rather than reloading the
 * list: the server decides what was stored, and a module's identity cannot change on a
 * replace.
 */
export class ModuleStore extends State {
  private static readonly COLLECTION = "/management/communities/{slug}/modules" as const;
  private static readonly ITEM = "/management/communities/{slug}/modules/{module_type}/{name}" as const;

  public readonly modules = new StateMap<string, ModuleSettings[]>();

  @stateProperty public loading = false;
  @stateProperty public error: ProblemError | null = null;

  private readonly api: ApiClient;

  public constructor(api: ApiClient) {
    super();
    this.api = api;
  }

  /** Modules for *slug*, or `undefined` when they have not been loaded yet. */
  public list(slug: string): ModuleSettings[] | undefined {
    return this.modules.get(slug);
  }

  public find(slug: string, id: ModuleId): ModuleSettings | undefined {
    return this.modules.get(slug)?.find((module) => moduleKey(module) === moduleKey(id));
  }

  public async load(slug: string): Promise<void> {
    this.loading = true;
    this.error = null;
    try {
      const modules = await this.api.GET(ModuleStore.COLLECTION, { params: { path: { slug } } });
      this.modules.set(slug, modules as ModuleSettings[]);
    } catch (error) {
      this.error = asProblem(error);
    } finally {
      this.loading = false;
    }
  }

  /** Load *slug*'s modules unless they are already cached. */
  public async ensure(slug: string): Promise<void> {
    if (!this.modules.has(slug)) await this.load(slug);
  }

  public async create(slug: string, module: ModuleSettings): Promise<ModuleSettings> {
    const created = (await this.api.POST(ModuleStore.COLLECTION, {
      params: { path: { slug } },
      // The body is a discriminated union the generated types spell out per variant; a
      // module built from a runtime schema cannot be narrowed to one of them here.
      body: module as never,
    })) as ModuleSettings;
    this.modules.set(slug, [...(this.modules.get(slug) ?? []), created]);
    return created;
  }

  public async replace(slug: string, id: ModuleId, module: ModuleSettings): Promise<ModuleSettings> {
    const replaced = (await this.api.PUT(ModuleStore.ITEM, {
      params: { path: { slug, module_type: id.type, name: id.name } },
      body: module as never,
    })) as ModuleSettings;

    const cached = this.modules.get(slug);
    if (cached !== undefined) {
      this.modules.set(
        slug,
        cached.map((existing) => (moduleKey(existing) === moduleKey(id) ? replaced : existing)),
      );
    }
    return replaced;
  }

  public async remove(slug: string, id: ModuleId): Promise<void> {
    await this.api.DELETE(ModuleStore.ITEM, {
      params: { path: { slug, module_type: id.type, name: id.name } },
    });
    const cached = this.modules.get(slug);
    if (cached !== undefined) {
      this.modules.set(
        slug,
        cached.filter((existing) => moduleKey(existing) !== moduleKey(id)),
      );
    }
  }

  /** Drop *slug*'s cache, so the next `ensure` refetches. */
  public invalidate(slug: string): void {
    this.modules.delete(slug);
  }
}
