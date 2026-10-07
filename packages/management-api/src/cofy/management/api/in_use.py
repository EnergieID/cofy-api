"""Refusing to delete a resource or secret that is still referenced."""

from __future__ import annotations

from typing import Any

from cofy.api.module import ModuleSettings
from cofy.api.references import references_in

from ..errors import ResourceInUseError


def check_unused(collection: str, name: str, modules: list[ModuleSettings], resources: list[Any]) -> None:
    """Refuse to delete the item `name` of `collection` while a module or resource references it."""
    users = [f"module {module.type}:{module.name}" for module in modules if _references(module, collection, name)]
    users += [f"resource {resource.name}" for resource in resources if _references(resource, collection, name)]
    if users:
        raise ResourceInUseError(f"{collection.capitalize()} {name!r} is still referenced by {', '.join(users)}")


def _references(settings: Any, collection: str, name: str) -> bool:
    return any(ref.name == name for ref in references_in(settings, collection))
