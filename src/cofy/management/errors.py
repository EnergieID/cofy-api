class ResourceNotFoundError(Exception):
    pass


class ResourceAlreadyExistsError(Exception):
    pass


def add_exception_handlers(app):
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.exception_handler(ResourceNotFoundError)
    async def handle_not_found_error(request: Request, exc: ResourceNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ResourceAlreadyExistsError)
    async def handle_conflict_error(request: Request, exc: ResourceAlreadyExistsError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(ValueError)
    async def handle_validation_error(request: Request, exc: ValueError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})
