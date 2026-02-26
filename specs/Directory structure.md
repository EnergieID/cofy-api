
```sh
src/
    cofy/                           # Core framework (installable package)
        __init__.py                 # Public API: CofyApi, CofyDB, CofyWorker, Module
        cofy_api.py                 # Main app class, handles settings and module registration
        module.py                   # Base Module class (abstract APIRouter)
        docs_router.py              # OpenAPI / docs endpoints
        token_auth.py               # Token-based authentication
        worker.py                   # Background worker implementation
        api/
            __init__.py             # Re-exports: DocsRouter, TokenInfo, token_verifier
        db/                         # Database utilities
            __init__.py             # Re-exports: Base, DatabaseBackedSource, TimestampMixin
        modules/                    # Grouping folder for domain modules (namespace package)
            <module_name>/
                __init__.py         # Public API for this module (re-exports)
                module.py           # Main module class: settings, route registration
                model.py            # Pydantic model(s) for the external API
                source.py           # Source interface and/or default implementation
                models/             # Optional: SQLAlchemy / DB models
                sources/            # Optional: data source implementations (DB, API, …)
                formats/            # Optional: formatters for the api output
                migrations/         # Optional: Alembic migrations (for DB-backed modules)
                tasks/              # Optional: background tasks related to this module
            timeseries/             # Generic timeseries module (base for tariff, etc.)
demo/                               # Dev demo application (not part of installed package)
    main.py                         # Demo application, showcases usage
    worker.py                       # Demo background worker, runs example jobs
    db/
        seed.py                     # Seed the database with example data
        migrate.py                  # Run all pending migrations
        reset.py                    # Drop all tables and re-run migrations
        generate.py                 # Generate a new migration for a module branch
tests/                              # Mirrors src/ structure
```