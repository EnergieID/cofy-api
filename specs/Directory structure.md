
```sh
src/
    cofy/                           # Core framework
        cofy_api.py                 # Main app class, handles settings and module registration
        docs_router.py              # OpenAPI / docs endpoints
        token_auth.py               # Token-based authentication
        worker.py                   # Background worker implementation
        db/                         # Database utilities
    shared/                         # Interfaces, generic implementations, abstract classes
        module.py                   # Base Module class (abstract APIRouter)
        timeseries/                 # Generic timeseries Module
    modules/
        <module_name>/
            module.py               # Main module class: settings, route registration
            model.py                # Pydantic model(s) for the external API
            source.py               # Source interface and/or default implementation
            models/                 # Optional: SQLAlchemy / DB models
            sources/                # Optional: data source implementations (DB, API, …)
            formats/                # Optional: formatters for the api output
            migrations/             # Optional: Alembic migrations (for DB-backed modules)
            tasks/                  # Optional: background tasks related to this module
    demo/
        main.py                     # Dev demo application, showcases usage
        worker.py                   # Demo background worker, runs example jobs
        db/
            seed.py                 # Seed the database with example data
            migrate.py              # Run all pending migrations
            reset.py                # Drop all tables and re-run migrations
            generate.py             # Generate a new migration for a module branch
tests/                              # Mirrors src/ structure
```