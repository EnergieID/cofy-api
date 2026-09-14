"""Domain errors and their mapping onto RFC 9457 `application/problem+json` responses."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

CONTENT_TYPE = "application/problem+json"


class ManagementError(Exception):
    """A failure with a defined HTTP representation.

    Subclasses set `status`, `title` and `code`, and are raised with a message that becomes
    the problem document's `detail`.
    """

    status: int = 500
    title: str = "Internal Server Error"
    code: str = "internal-error"


class ResourceNotFoundError(ManagementError):
    status = 404
    title = "Not Found"
    code = "resource-not-found"


class ResourceAlreadyExistsError(ManagementError):
    status = 409
    title = "Conflict"
    code = "resource-already-exists"


class ValidationFailedError(ManagementError):
    status = 422
    title = "Unprocessable Content"
    code = "validation-failed"


def problem(
    status: int,
    title: str,
    detail: str,
    code: str,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    """Build a problem+json response.

    `code` names the failure in a way a client can act on - to translate it, or to branch on
    it - where `title` and `detail` are English prose meant for a person. It takes the place
    RFC 9457's `type` would have: that member is a URI, and inventing one that resolves to
    nothing helps nobody.
    """
    body: dict[str, Any] = {"title": title, "status": status, "detail": detail, "code": code}
    if errors:
        body["errors"] = errors
    return JSONResponse(status_code=status, content=body, media_type=CONTENT_TYPE)


def add_exception_handlers(app: FastAPI) -> None:
    """Register the problem+json handlers on *app*."""

    @app.exception_handler(ManagementError)
    async def handle_management_error(request: Request, exc: ManagementError) -> JSONResponse:
        return problem(exc.status, exc.title, str(exc), exc.code)

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # `loc` is passed through as pydantic reports it, and `type` with it: that is pydantic's
        # own stable code for the failure, which is what lets a client translate the message
        # rather than show this English one. `input` is dropped: it echoes the submitted value,
        # which for a credential field would put the secret in the response.
        errors = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return problem(
            422,
            ValidationFailedError.title,
            "Request validation failed.",
            ValidationFailedError.code,
            errors,
        )

    @app.exception_handler(ValueError)
    async def handle_value_error(request: Request, exc: ValueError) -> JSONResponse:
        # Domain invariants that are not tied to a single input field - a body whose identity
        # disagrees with its URL, a stored config that is not a mapping.
        return problem(422, ValidationFailedError.title, str(exc), ValidationFailedError.code)
