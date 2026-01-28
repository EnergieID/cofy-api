from collections.abc import Callable

from fastapi import APIRouter, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse


class DocsRouter(APIRouter):
    def __init__(self, get_openapi: Callable[[], dict]):
        super().__init__()
        self.get_openapi = get_openapi
        self.add_api_route(
            "/docs",
            self.get_swagger_ui_html,
            include_in_schema=False,
        )
        self.add_api_route(
            "/openapi.json",
            self.get_openapi,
            include_in_schema=False,
        )

    async def get_swagger_ui_html(self, request: Request):
        response = get_swagger_ui_html(
            openapi_url="/openapi.json",
            title="Docs",
            swagger_ui_parameters={
                "spec": self.get_openapi(),
                "onComplete": "AUTHORIZE_API",
            },
        )

        if hasattr(request.state, "auth_info"):
            content = response.body.decode()
            content = content.replace(
                '"AUTHORIZE_API"',
                f'() => ui.preauthorizeApiKey("{request.state.auth_info["scheme"]}", "{request.state.auth_info["content"]}")',
            )
            response = HTMLResponse(content=content, status_code=response.status_code)
        return response
