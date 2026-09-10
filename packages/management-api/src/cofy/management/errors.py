"""Domain errors and their mapping onto RFC 9457 `application/problem+json` responses."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

CONTENT_TYPE = "application/problem+json"


class ManagementError(Exception):
    """A failure with a defined HTTP representation.

    Subclasses set `status` and `title`, and are raised with a message that becomes the
    problem document's `detail`.
    """

    status: int = 500
    title: str = "Internal Server Error"


class ResourceNotFoundError(ManagementError):
    status = 404
    title = "Not Found"


class ResourceAlreadyExistsError(ManagementError):
    status = 409
    title = "Conflict"


class ValidationFailedError(ManagementError):
    status = 422
    title = "Unprocessable Content"


def problem(status: int, title: str, detail: str, errors: list[dict[str, Any]] | None = None) -> JSONResponse:
    """Build a problem+json response.

    `type` is left out, which RFC 9457 defines as equivalent to `about:blank`: there is no
    documentation to point it at, and inventing a URI that resolves to nothing helps nobody.
    """
    body: dict[str, Any] = {"title": title, "status": status, "detail": detail}
    if errors:
        body["errors"] = errors
    return JSONResponse(status_code=status, content=body, media_type=CONTENT_TYPE)


def add_exception_handlers(app: FastAPI) -> None:
    """Register the problem+json handlers on *app*."""

    @app.exception_handler(ManagementError)
    async def handle_management_error(request: Request, exc: ManagementError) -> JSONResponse:
        return problem(exc.status, exc.title, str(exc))

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # `loc` is passed through as pydantic reports it. `input` is dropped: it echoes the
        # submitted value, which for a credential field would put the secret in the response.
        errors = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return problem(422, ValidationFailedError.title, "Request validation failed.", errors)

    @app.exception_handler(ValueError)
    async def handle_value_error(request: Request, exc: ValueError) -> JSONResponse:
        # Domain invariants that are not tied to a single input field - a body whose identity
        # disagrees with its URL, a stored config that is not a mapping.
        return problem(422, ValidationFailedError.title, str(exc))
