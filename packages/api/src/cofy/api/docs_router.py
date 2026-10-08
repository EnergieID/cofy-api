from collections.abc import Callable

from fastapi import APIRouter, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse


class DocsRouter(APIRouter):
    """
    Overrides default FastAPI docs behavior to include security.
    """

    def __init__(self, get_openapi: Callable[[Request], dict]):
        super().__init__()
        self.get_openapi = get_openapi
        self.add_api_route(
            "/docs",
            self.get_swagger_ui_html,
            include_in_schema=False,
        )
        self.add_api_route(
            "/openapi.json",
            self.openapi,
            include_in_schema=False,
        )

    def openapi(self, request: Request) -> dict:
        # Not `get_openapi` itself as the endpoint: FastAPI only passes the request to a parameter typed `Request`
        # exactly, and `CofyAPI.openapi` can also be called without one.
        return self.get_openapi(request)

    async def get_swagger_ui_html(self, request: Request):
        response = get_swagger_ui_html(
            openapi_url="/openapi.json",
            title="Docs",
            swagger_ui_parameters={
                "spec": self.openapi(request),
                "onComplete": "AUTHORIZE_API",
            },
        )

        if hasattr(request.state, "auth_info"):
            assert isinstance(response.body, bytes)
            content = response.body.decode()
            content = content.replace(
                '"AUTHORIZE_API"',
                f'() => ui.preauthorizeApiKey("{request.state.auth_info["scheme"]}", "{request.state.auth_info["content"]}")',
            )
            response = HTMLResponse(content=content, status_code=response.status_code)
        return response
