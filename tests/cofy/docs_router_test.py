from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from src.cofy.docs_router import DocsRouter


class TestDocsRouter:
    def setup_method(self):
        self.docs_router = DocsRouter(
            lambda: {
                "openapi": "3.0.0",
                "info": {
                    "title": "Test API",
                    "version": "0.1.0",
                },
                "paths": {
                    "/dummy": {
                        "get": {
                            "responses": {
                                "200": {
                                    "description": "Successful Response",
                                }
                            }
                        }
                    }
                },
            }
        )
        self.app = FastAPI(
            docs_url=None,
            redoc_url=None,
            openapi_url=None,
        )
        self.app.include_router(self.docs_router)
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
