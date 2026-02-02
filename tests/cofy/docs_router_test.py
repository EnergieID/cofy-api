from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route

from src.cofy.docs_router import DocsRouter


# Dummy endpoint for testing
async def dummy_endpoint(request: Request):
    return {"message": "ok"}


class TestDocsRouter:
    def setup_method(self):
        routes = [Route("/dummy", dummy_endpoint)]
        self.docs_router = DocsRouter(title="Test API", version="0.1.0", routes=routes)
        self.app = FastAPI(
            docs_url=None,
            redoc_url=None,
            openapi_url=None,
        )
        self.app.include_router(self.docs_router)
        for route in routes:
            self.app.router.routes.append(route)
        self.client = TestClient(self.app)

    def test_openapi_json(self):
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "Test API"
        assert data["info"]["version"] == "0.1.0"
        assert "paths" in data

    def test_docs_html(self):
        response = self.client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "swagger-ui" in response.text.lower()

    def test_docs_html_with_token_and_auth_scheme(self):
        class CustomMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                request.state.auth_info = {
                    "scheme": "bar",
                    "content": "bearer foo",
                }
                return await call_next(request)

        # ty can't handle this type properly, see https://github.com/Kludex/starlette/discussions/2451 and https://github.com/astral-sh/ty/issues/903
        self.app.add_middleware(CustomMiddleware)  # ty: ignore[invalid-argument-type]
        response = self.client.get("/docs")
        assert response.status_code == 200
        assert 'ui.preauthorizeApiKey("bar", "bearer foo")' in response.text
