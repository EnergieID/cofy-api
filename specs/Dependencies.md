## Project management
 - **ruff**: Linting and code formatting
 - **uv**: Dependency management and virtual environments
 - **ty**: Type checking
 - **poethepoet**: Task runner for development tasks
 
## Core dependencies
### [Narwhals](https://github.com/narwhals-dev/narwhals)
- Use for dataframes: this way we can easilly support multiple data frameworks from other libaries
- this will mainly be relevant for our internal API
- source layer can work with pandas, polars, dask, etc, they can all easily be converted to narwhals dataframes

### [FastAPI](https://fastapi.tiangolo.com/)
- We use this as our standard web framework for building the cofy cloud api

## Module specific dependencies
- entsoe-py: used by the Tariff module as default source for entsoe data

## Future exploration
Dependencies we might want to explore in the future
## [Pydantic](https://pydantic.dev/)
- data validation and settings management using python type annotations
## [Pandera](https://pandera.readthedocs.io/en/stable/)
- Typing for Datframe schemas
