"""A community using every kind of reference, for the resource, secret and usage tests."""

from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cofy.management.api.allowed_resources import AllowedResourcesRouter
from cofy.management.api.modules import ModulesRouter
from cofy.management.api.resources import ResourcesRouter
from cofy.management.api.secrets import SecretsRouter
from cofy.management.errors import add_exception_handlers
from cofy.management.persitance.file.modules import FileModulesPersistence
from cofy.management.persitance.file.resources import FileResourcesPersistence
from cofy.management.persitance.file.secrets import FileSecretsPersistence

COMMUNITY = "/management/communities/test"


def ref(name: str) -> dict:
    return {"type": "resource", "name": name}


def write_community(path: Path) -> None:
    """Two secrets - one used by a source resource, one by nothing - two sources, and a module using one."""
    community = {
        "type": "cofy_api",
        "secrets": [
            {"name": "entsoe_key", "description": "ENTSO-E", "value": "secret-key"},
            {"name": "spare_key", "value": "spare-secret"},
        ],
        "resources": [
            {
                "type": "source",
                "name": "day_ahead",
                "value": {
                    "type": "entsoe_day_ahead",
                    "api_key": {"type": "secret", "name": "entsoe_key"},
                    "country_code": "BE",
                },
            },
            {
                "type": "source",
                "name": "unused",
                "value": {"type": "entsoe_day_ahead", "api_key": {"type": "secret", "name": "entsoe_key"}},
            },
        ],
        "modules": [{"type": "tariff", "name": "spot", "source": ref("day_ahead")}],
    }
    (path / "test.yaml").write_text(yaml.safe_dump(community))


def client_for(path: Path) -> TestClient:
    app = FastAPI()
    add_exception_handlers(app)
    modules, resources, secrets = (
        FileModulesPersistence(path),
        FileResourcesPersistence(path),
        FileSecretsPersistence(path),
    )
    app.include_router(ModulesRouter(modules).router)
    app.include_router(ResourcesRouter(resources, modules).router)
    app.include_router(SecretsRouter(secrets, modules, resources).router)
    app.include_router(AllowedResourcesRouter().router)
    return TestClient(app, raise_server_exceptions=False)


def stored(path: Path) -> dict:
    return yaml.safe_load((path / "test.yaml").read_text())
