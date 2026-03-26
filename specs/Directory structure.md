
```sh
src/
    cofy/                           # Core framework (installable package)
        __init__.py                 # Public API: CofyAPI, Module
        api/
            cofy_api.py                 # Main app class, handles settings and module registration
            module.py                   # Base Module class (abstract APIRouter)
            docs_router.py              # OpenAPI / docs endpoints
            token_auth.py               # Token-based authentication
        modules/                    # Grouping folder for domain modules (namespace package)
            <module_name>/
                __init__.py         # Public API for this module (re-exports)
                module.py           # Main module class: settings, route registration
                model.py            # Pydantic model(s) for the external API
                source.py           # Source interface and/or default implementation
                sources/            # Optional: data source implementations (DB, API, …)
                formats/            # Optional: formatters for the api output
                tasks/              # Optional: background tasks related to this module
            timeseries/             # Generic timeseries module (base for tariff, etc.)
demo/                               # Dev demo application (not part of installable package)
    main.py                         # Example app tying everything together
    data/                           # Example data for the demo app
tests/                              # Mirrors src/ structure
```