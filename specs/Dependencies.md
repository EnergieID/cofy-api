## Project management
 - **ruff**: Linting and code formatting
 - **uv**: Dependency management and virtual environments
 - **ty**: Type checking
 - **poethepoet**: Task runner for development tasks
 - **pre-commit**: Git hooks for code quality enforcement
 - **pytest**: Testing framework
 
## Core dependencies
### [Narwhals](https://github.com/narwhals-dev/narwhals)
- Use for dataframes: this way we can easilly support multiple data frameworks from other libaries
- this will mainly be relevant for our internal API
- source layer can work with pandas, polars, dask, etc, they can all easily be converted to narwhals dataframes

### [FastAPI](https://fastapi.tiangolo.com/)
- We use this as our standard web framework for building the cofy cloud api

### [Pydantic](https://pydantic.dev/)
- data validation using python type annotations

### [SQLAlchemy](https://www.sqlalchemy.org/)
- For database interactions in our default db source implementations
- We use **[alembic](https://alembic.sqlalchemy.org/en/latest/)** for database migrations

### [saq](https://pypi.org/project/saq/)
- For running and scheduling background jobs in our default worker implementation

## Module specific dependencies
- entsoe-py: used by the Tariff module as default source for entsoe data

## Future exploration
Dependencies we might want to explore in the future
### [Pandera](https://pandera.readthedocs.io/en/stable/)
- Typing for Datframe schemas (Does not support narwhals yet, but might be interesting to explore in the future for our internal API)
