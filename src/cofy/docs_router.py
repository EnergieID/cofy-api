from fastapi import APIRouter, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
from starlette.routing import BaseRoute


class DocsRouter(APIRouter):
    _title: str
    _version: str
    _routes: list[BaseRoute]

    def __init__(self, title: str, version: str, routes: list[BaseRoute]):
        super().__init__()
        self._title = title
        self._version = version
        self._routes = routes
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

    async def get_openapi(self):
        return get_openapi(
            title=self._title,
            version=self._version,
            routes=self._routes,
        )

    async def get_swagger_ui_html(self, request: Request):
        t = request.state.token if hasattr(request.state, "token") else None
        openapi_url = f"{self.prefix}/openapi.json"
        if t:
            openapi_url += f"?token={t}"
        response = get_swagger_ui_html(
            openapi_url=openapi_url,
            title=f"{self._title} - Docs",
            swagger_ui_parameters={
                "onComplete": "AUTHORIZE_API",
            },
        )

        if t and hasattr(request.state, "auth_scheme_used"):
            content = response.body.decode()
            content = content.replace(
                '"AUTHORIZE_API"',
                f'() => ui.preauthorizeApiKey("{request.state.auth_scheme_used}", "{t}")',
            )
            response = HTMLResponse(content=content, status_code=response.status_code)
        return response
