
## Step-by-step plan: Management API

The plan has 5 phases, each independently testable. No breaking changes to the existing `CofyAPI` until Phase 3.

---

### Phase 1 — Foundation: Factory Pattern + Registry

**Step 1.1 — Restore the DB module**

The `cofy.db` package exists in db but was removed from src. The pyproject.toml still references it. Port it back to `src/cofy/db/` — `CofyDB`, `Base`, `DatabaseBackedSource`, `TimestampMixin` all come for free.

**Step 1.2 — Add a `Settings` model to each source**

For every source class (`EntsoeDayAheadTariffSource`, `EnergyCostTariffSource`, `MembersFileSource`, `EnergyIDProduction`, etc.), add a corresponding Pydantic `Settings` model:

```python
class EntsoeDayAheadSourceSettings(BaseModel):
    api_key: SecretStr = Field(json_schema_extra={"writeOnly": True})
    country_code: str = Field(default="NL", examples=["NL", "BE", "DE"])
```

The existing `__init__` signature on each source is the spec — just model it with Pydantic. No other changes to the source classes yet.

**Step 1.3 — Add `SourceFactory` and `ModuleFactory` abstractions**

New file `src/cofy/registry.py`:

```python
class SourceFactory(ABC):
    source_type: str          # e.g. "entsoe_day_ahead"
    display_name: str
    SettingsModel: type[BaseModel]
    
    @abstractmethod
    def build(self, settings: BaseModel) -> object: ...

class ModuleFactory(ABC):
    module_type: str          # e.g. "tariff"
    display_name: str
    SettingsModel: type[BaseModel]  # module-level settings (name, description, etc.)
    compatible_sources: list[str]   # source_type strings
    
    @abstractmethod
    def build(self, settings: BaseModel, source: object) -> Module: ...
```

**Step 1.4 — Implement factories for all existing module+source combinations**

One factory class per module type, one per source type. Register them all in a `Registry` singleton. The registry also discovers third-party factories via entry points:

```python
# importlib.metadata.entry_points(group="cofy.modules")
# importlib.metadata.entry_points(group="cofy.sources")
```

**Step 1.5 — Add `GET /available-modules` endpoint to a new `RegistryRouter`**

Returns all registered module types, their `model_json_schema()`, their compatible sources and each source's schema. This is the endpoint the future management frontend will use to render forms. Test it works correctly at this step.

---

### Phase 2 — Community Data Model

**Step 2.1 — Define Pydantic config schemas**

```python
class ActiveModuleConfig(BaseModel):
    module_type: str          # "tariff"
    instance_name: str        # "entsoe" — becomes the URL slug
    source_type: str          # "entsoe_day_ahead"
    module_settings: dict     # validated against ModuleFactory.SettingsModel
    source_settings: dict     # validated against SourceFactory.SettingsModel

class CommunityConfig(BaseModel):
    slug: str                 # URL-safe, unique
    name: str
    modules: list[ActiveModuleConfig]
    allowed_module_types: list[str]  # set by server admin
```

A `CommunityConfig.build_api() -> CofyAPI` method does exactly what main.py does today — but driven by data, not code.

**Step 2.2 — SQLAlchemy models**

Two new tables (separate from the existing module-level DB infrastructure):

- `communities`: `id`, `slug` (unique), `name`, `created_at`, `updated_at`
- `active_modules`: `id`, `community_id` (FK), `module_type`, `instance_name`, `source_type`, `module_settings` (JSON), `source_settings` (JSON), `created_at`, `updated_at`

Use the existing `TimestampMixin` and `Base` from `cofy.db`.

**Step 2.3 — Alembic migration**

Generate the migration for the two new tables using the existing `CofyDB.generate_migration()` infrastructure. This is already set up.

**Step 2.4 — Repository layer**

Plain functions (not a class) in `src/cofy/management/repository.py`, taking a SQLAlchemy `Session`:

```python
def get_community(session, slug: str) -> Community | None
def list_communities(session) -> list[Community]
def create_community(session, config: CommunityConfig) -> Community
def update_community(session, slug: str, config: CommunityConfig) -> Community
def delete_community(session, slug: str) -> None
def list_modules(session, slug: str) -> list[ActiveModule]
def upsert_module(session, slug: str, config: ActiveModuleConfig) -> ActiveModule
def delete_module(session, slug: str, instance_name: str) -> None
```

---

### Phase 3 — Multi-Tenant Host

**Step 3.1 — `CofyHost`**

New class `src/cofy/host.py`. A FastAPI app that:
- Holds a `dict[str, CofyAPI]` of mounted communities
- On startup (`lifespan`): opens DB, loads all communities, calls `mount_community()` for each
- `mount_community(slug, api)`: calls `self.mount(f"/{slug}", api)`
- `unmount_community(slug)`: removes from the router tree (Starlette supports this via `app.routes`)
- `reload_community(slug, config)`: unmount + remount with new config

**Step 3.2 — Demo migration**

Replace main.py's imperative code with a `community.yaml` (or load from DB). The demo still runs identically — this validates the whole factory chain end-to-end before touching the management API.

---

### Phase 4 — Management REST API

**Step 4.1 — Server admin router**

`src/cofy/management/admin_router.py`, mounted at `/admin/` on `CofyHost`:

```
GET    /admin/communities                          list all
POST   /admin/communities                          create (validates config, builds + mounts CofyAPI)
GET    /admin/communities/{slug}                   get one
PUT    /admin/communities/{slug}                   update (reload)
DELETE /admin/communities/{slug}                   delete (unmount)
GET    /admin/communities/{slug}/modules           list modules
POST   /admin/communities/{slug}/modules           add module (hot-reload community)
PUT    /admin/communities/{slug}/modules/{name}    update module (hot-reload)
DELETE /admin/communities/{slug}/modules/{name}    remove module (hot-reload)
GET    /admin/available-modules                    registry introspection (schema for forms)
```

All write operations: persist to DB first, then reload the live community. If `CommunityConfig.build_api()` raises (bad settings), return `422` and roll back — the live community is untouched.

**Step 4.2 — Community admin router**

`src/cofy/management/community_admin_router.py`, mounted at `/{slug}/manage/` on each `CofyAPI`:

```
GET    /{slug}/manage/config             get own community config
PUT    /{slug}/manage/modules/{name}     update own module settings
POST   /{slug}/manage/modules            add module (within allowed_module_types)
DELETE /{slug}/manage/modules/{name}     remove module
```

The key constraint: this router can only use module types in `community.allowed_module_types`. Attempts to use others return `403`.

---

### Phase 5 — Auth

**Step 5.1 — JWT/OIDC validator**

Replace `token_verifier` for the management API with a proper JWKS-based validator. Add a new dependency `src/cofy/management/auth.py`:

```python
def require_server_admin(token: str = Depends(oauth2_scheme)) -> Claims:
    # Fetch JWKS from issuer URL, validate signature, check role claim

def require_community_admin(slug: str, token: str = Depends(oauth2_scheme)) -> Claims:
    # Validate JWT, check community_id claim matches slug
```

Configuration (from env vars or `CofyHost` config):
```
OIDC_ISSUER_URL=https://keycloak.example.com/realms/cofy
OIDC_AUDIENCE=cofy-management
```

The existing `token_verifier` stays untouched — it remains valid for protecting individual `CofyAPI` instances via static tokens (or can be switched to OIDC per community, that's a community-level config choice).

**Step 5.2 — Apply auth dependencies**

- All `/admin/` routes: `Depends(require_server_admin)`
- All `/{slug}/manage/` routes: `Depends(require_community_admin)`
- Individual `CofyAPI` auth: unchanged, configured per community in `CommunityConfig`

---

### Dependency map

```
Phase 1 (factory + registry)
    └── Phase 2 (data model + DB)
            └── Phase 3 (CofyHost)
                    └── Phase 4 (management API)
                            └── Phase 5 (auth)
```

Each phase has a clear "done" state you can test independently. After Phase 3, the demo should already work from a `community.yaml` file. After Phase 4, you have a fully functional management API with no auth (suitable for local dev). Auth is the last addition.