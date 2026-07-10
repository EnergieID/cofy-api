
## Multi-tenant database architecture

### The three options

1. **Separate databases** — maximum isolation, operationally complex (connection pools per tenant, separate backup jobs). Overkill here.
2. **Schema-per-tenant** — one Postgres database, each community gets its own schema (`community_demo`, `community_brugge`). Good isolation, PostgreSQL native.
3. **Shared schema + `tenant_id`** — all communities share tables, filtered by a `community_id` column.

### Why schema-per-tenant is the right fit for Cofy

The "different modules per community" requirement is what settles this. With a shared schema:
- Community A has a members module, community B doesn't — you end up with a members table full of NULLs for B, or worse, JSONB columns that lose type safety
- Alembic migrations have to account for all possible module combinations in one schema
- You must remember `WHERE community_id = ?` on every query — one missed filter leaks data

With schema-per-tenant:
- Community A's schema has a `members` table. Community B's schema simply doesn't. The structure reflects reality.
- `DROP SCHEMA community_demo CASCADE` cleanly removes all of a community's operational data
- Cross-tenant data leakage is structurally impossible at the query level — wrong schema, wrong tables
- Each community schema runs only the migrations for its active modules

PostgreSQL has first-class support for this via `search_path`. SQLAlchemy handles it with `schema=` on table definitions or by setting the search path on the connection.

### The hybrid: global settings + per-community data schemas

This is the cleanest split:

```
public schema (management plane)
├── communities          ← id, slug, name, allowed_module_types
├── active_modules       ← community_id, module_type, source_type, settings (JSON)
└── (future: users, roles, audit_log)

community_demo schema (data plane)
├── members              ← created by MembersModule migration
├── production_readings  ← created by ProductionModule migration
└── alembic_version      ← per-schema migration tracking

community_brugge schema
├── members
└── alembic_version
```

**Settings stay in the global schema.** They are management data — they tell the system *how* to configure a community, not *what* that community has collected. Putting them in the community schema would mean the system needs to read that schema just to know what to mount, which creates a chicken-and-egg problem on startup.

### Alembic with this pattern

This fits the existing `DatabaseBackedSource` / `CofyDB` architecture naturally. When a new community is created:

1. Create the Postgres schema: `CREATE SCHEMA community_{slug}`
2. Set `search_path` to that schema
3. Run only the migrations for that community's active modules against it

The `migration_locations` property on each `DatabaseBackedSource` already separates migrations by module. You extend this to also be schema-aware: each community's schema tracks its own `alembic_version` table, so migrations for community A and community B are fully independent.

When a module is added to a community mid-lifecycle, you run just that module's migrations against that community's schema. No other community is touched.

### The one trade-off to be aware of

**Server-admin cross-community analytics** (e.g., "total production across all communities") requires querying across schemas. This isn't hard — you either:
- Use `UNION ALL` queries across schemas (fine for occasional admin queries)
- Maintain an aggregation/reporting table in the global schema that modules write into (better for frequent analytics)

At your current scale this isn't a concern, but worth knowing it's the main cost of the schema-per-tenant approach.