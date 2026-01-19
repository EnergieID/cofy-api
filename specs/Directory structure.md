
```sh
/src
    modules/
        <module_name>/
            apps/            # Optional: if app.py becomes to complex
            apis/            # Optional: if multiple implementations of api, or API becomes complex
            models/          # Optional: if module specifies multiple models
            sources/         # Data source layer: DB clients, proxies, interfaces
            parsers/          # Parse layer: adapters, converters, custom logic
            compute/        # Compute layer: pure functions, stateless logic
            jobs/           # Scheduled jobs: fetch, parse, store, reformat, post
            __init__.py     # Makes the module importable
            app.py          # Main imported class, should handle settings and expose API
            api.py          # Fast api app, with all endpoints
            model.py        # The model used by the external API
    shared/             # Interfaces, generic implementations, abstract classes, etc,...
        ...             # Same layers as every module
    cofy/
        app.py          # Main app, handles settings and module registration
        api.py          # contains general FastAPI endpoints
    test/
        ...
    demo/               
        main.py         # dev demo application, showcase usages and allows manual testing
```