"""Every route of the management API is guarded by exactly one policy rule, so none is left open by forgetting one."""

from __future__ import annotations

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute, iter_route_contexts

from cofy.management.auth.access import Subject
from cofy.management.main import app
from cofy.management.policies.policy import PolicyCheck, PolicyRouter


def unguarded_routes(app: FastAPI) -> list[str]:
    # Included routers are kept as routers rather than copied in, so the routes are walked through them.
    return [
        f"{sorted(context.methods or [])} {context.path}"
        for context in iter_route_contexts(app.routes)
        if isinstance(context.original_route, APIRoute)
        and sum(isinstance(dependency.dependency, PolicyCheck) for dependency in context.dependencies) != 1
    ]


def test_the_routes_are_actually_walked():
    assert len(list(iter_route_contexts(app.routes))) > 30


def test_every_route_is_guarded_by_one_rule():
    assert unguarded_routes(app) == []


def test_a_route_from_a_plain_router_is_caught():
    router = APIRouter()
    router.add_api_route("/open", lambda: None, methods=["GET"])
    unguarded = FastAPI()
    unguarded.include_router(router)

    assert unguarded_routes(unguarded) == ["['GET'] /open"]


def test_a_policy_router_refuses_a_route_without_a_rule():
    router = PolicyRouter(subject=Subject.modules)

    with pytest.raises(TypeError, match="rule"):
        router.add_api_route("/open", lambda: None, methods=["GET"])  # ty: ignore[missing-argument]


def test_a_policy_router_refuses_the_route_decorators():
    router = PolicyRouter(subject=Subject.modules)

    with pytest.raises(TypeError, match="rule"):
        router.get("/open")(lambda: None)
