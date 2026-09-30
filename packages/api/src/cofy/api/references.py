"""References to named resources, and how they are checked and resolved."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, GetCoreSchemaHandler, GetJsonSchemaHandler, PrivateAttr
from pydantic_core import core_schema

from .from_settings_mixin import BaseSettingsModel


class RefSettings(BaseSettingsModel):
    """A reference to a named resource."""

    type: Literal["ref"] = "ref"
    name: str = Field(description="The name of the referenced resource.")

    # Stamped by the field it was validated for, which knows what it accepts.
    _field: Referable | None = PrivateAttr(default=None)

    def convert(self) -> Any:
        resolver = _resolver.get()
        if resolver is None:
            raise RuntimeError(f"Reference to {self.name!r} can only be resolved while its configuration is built")
        return resolver.get(self.name)


def _is_ref(value: Any) -> bool:
    return isinstance(value, RefSettings) or (isinstance(value, dict) and value.get("type") == "ref")


@dataclass(frozen=True)
class Referable:
    """Annotates a field whose value can also be a reference to a resource of `kind`.

    For a field holding a member of `family`, only resources holding one of its members fit.
    """

    kind: str
    family: type[BaseSettingsModel] | None = None

    def types(self) -> list[str] | None:
        """The types of value a resource must hold to fit, or None if any does."""
        return sorted(self.family.registry()) if self.family is not None else None

    def __get_pydantic_core_schema__(self, source: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        def stamp(ref: RefSettings) -> RefSettings:
            ref._field = self
            return ref

        return core_schema.tagged_union_schema(
            {
                "value": handler(source),
                "ref": core_schema.no_info_after_validator_function(stamp, handler.generate_schema(RefSettings)),
            },
            discriminator=lambda value: "ref" if _is_ref(value) else "value",
        )

    def __get_pydantic_json_schema__(self, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler) -> Any:
        json_schema = handler(schema)
        types = self.types()
        # The value is the first of the two branches, the reference the second.
        json_schema["x-referable"] = {"kind": self.kind} | ({"types": types} if types is not None else {})
        return json_schema


class ResourceResolver:
    """Builds each resource once, the first time it is referenced, so every reference shares it."""

    def __init__(self, resources: Sequence[Any]):
        self._resources = {resource.name: resource for resource in resources}
        self._built: dict[str, Any] = {}
        self._building: list[str] = []

    def get(self, name: str) -> Any:
        if name not in self._built:
            if name in self._building:
                raise ValueError(f"Resource {name!r} references itself")
            self._building.append(name)
            try:
                self._built[name] = self._resources[name].convert().value
            finally:
                self._building.pop()
        return self._built[name]


_resolver: ContextVar[ResourceResolver | None] = ContextVar("resource_resolver", default=None)


@contextmanager
def resolving(resources: Sequence[Any]) -> Iterator[None]:
    """Resolve references to `resources` while the block builds a configuration."""
    token = _resolver.set(ResourceResolver(resources))
    try:
        yield
    finally:
        _resolver.reset(token)


def iter_models(value: Any) -> Iterator[BaseModel]:
    """Every model in `value`, at any depth."""
    if isinstance(value, BaseModel):
        yield value
        for name in type(value).model_fields:
            yield from iter_models(getattr(value, name))
    elif isinstance(value, list | tuple):
        for item in value:
            yield from iter_models(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_models(item)


def references_in(value: Any) -> list[RefSettings]:
    """Every reference in `value`, at any depth."""
    return [model for model in iter_models(value) if isinstance(model, RefSettings)]


def check_references(resources: Sequence[Any], *configured: Any) -> None:
    """Check that `resources` have unique names, and every reference in them and in `configured` fits a resource."""
    by_name: dict[str, Any] = {}
    for resource in resources:
        if resource.name in by_name:
            raise ValueError(f"Resource name {resource.name!r} is used more than once")
        by_name[resource.name] = resource

    refs = references_in([*configured, *resources])
    for ref in refs:
        if ref.name not in by_name:
            raise ValueError(f"Reference to unknown resource {ref.name!r}")

    uses = {resource.name: {ref.name for ref in references_in(resource.value)} for resource in resources}
    for name in uses:
        _check_acyclic(name, uses, [])

    for ref in refs:
        _check_fits(ref, by_name)


def _check_fits(ref: RefSettings, by_name: dict[str, Any]) -> None:
    field = ref._field
    if field is None:
        return
    resource = by_name[ref.name]
    if resource.type != field.kind:
        raise ValueError(f"Resource {ref.name!r} is a {resource.type}, where a {field.kind} is expected")
    # A resource can itself just reference another one, so what it holds is at the end of that chain.
    while isinstance(resource.value, RefSettings):
        resource = by_name[resource.value.name]
    held = getattr(resource.value, "type", None)
    types = field.types()
    if types is not None and held not in types:
        raise ValueError(f"Resource {ref.name!r} holds a {held} source, where one of {', '.join(types)} is expected")


def _check_acyclic(name: str, uses: dict[str, set[str]], path: list[str]) -> None:
    if name in path:
        raise ValueError(f"Resources reference each other in a cycle: {' -> '.join([*path[path.index(name) :], name])}")
    for used in sorted(uses[name]):
        _check_acyclic(used, uses, [*path, name])
