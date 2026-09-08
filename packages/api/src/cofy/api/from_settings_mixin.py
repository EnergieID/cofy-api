from __future__ import annotations

import sys
from functools import reduce
from operator import or_
from typing import Annotated, Any, ClassVar

from pydantic import BaseModel, Field


def _resolve(value: Any) -> Any:
    """Recursively convert any BaseSettingsModel instances to their actual objects."""
    if isinstance(value, BaseSettingsModel):
        return value.convert()
    if isinstance(value, list):
        return [_resolve(v) for v in value]
    if isinstance(value, dict):
        return {_resolve(k): _resolve(v) for k, v in value.items()}
    return value


# Every settings model wired to a FromSettingsMixin class, in registration order.
_registered_settings: list[type[BaseSettingsModel]] = []
# How many of those were already reflected in the published unions, so that finalize() can
# tell whether anything registered since it last ran.
_resolved_count = 0
_resolving = False


class BaseSettingsModel(BaseModel):
    _model: ClassVar[Any]  # wired automatically on registration

    def convert(self) -> Any:
        kwargs = {name: _resolve(getattr(self, name)) for name in self.__class__.model_fields if name != "type"}
        return self._model(**kwargs)

    @classmethod
    def union_type(cls) -> Any:
        """Return a discriminated union of every settings model registered under `cls`."""
        finalize()
        registry = getattr(cls._model, "_registry", {})
        union = reduce(or_, registry.values())
        return Annotated[union, Field(discriminator="type")]

    @classmethod
    def union_alias(cls) -> str:
        """Name under which `settings`' discriminated union is published to settings modules."""
        return f"Any{cls.__name__}"


def finalize(*, force: bool = False) -> None:
    """Publish the `Any<Name>` union aliases and rebuild every settings model.

    Runs automatically whenever a resolved model is needed - reading a union via
    `union_type()`, or building an object via `create()` - and returns immediately if
    nothing has registered since it last ran. Calling it explicitly after discovery is
    therefore optional, and mainly serves to make an application's startup order obvious.

    It is deliberately not run per registration: that would rebuild every settings model
    once per registered type, and would publish unions that are still missing the types
    imported later in the same discovery pass.

    Note that a union already *captured* into a variable is a snapshot - a type registered
    afterwards will not appear in it, so read `union_type()` after discovery, not before.
    """
    global _resolved_count, _resolving

    if _resolving:
        return  # re-entered via union_type() while publishing; the outer call completes it
    if not force and _resolved_count == len(_registered_settings):
        return  # nothing registered since the last run

    _resolving = True
    try:
        settings_models = list(_registered_settings)
        aliases = {settings.union_alias(): settings.union_type() for settings in settings_models}
        modules = {sys.modules[settings.__module__] for settings in settings_models}

        # Bind every alias everywhere first: a settings model may reference a union whose
        # members live in other modules, so all names must exist before anything is rebuilt.
        for module in modules:
            for name, union in aliases.items():
                setattr(module, name, union)

        for settings in settings_models:
            _reresolve_alias_fields(settings, aliases)
            settings.model_rebuild(force=True)

        _resolved_count = len(settings_models)
    finally:
        _resolving = False


def _reresolve_alias_fields(settings: type[BaseSettingsModel], aliases: dict[str, Any]) -> None:
    """Re-evaluate the fields of `settings` that are annotated with a union alias.

    On the first pass the aliases are still unresolved names, so pydantic resolves them
    itself when the model is built. On any later pass they are already resolved to the
    union as it stood back then, and `model_rebuild()` reuses that stale annotation rather
    than re-reading the source - so a type registered afterwards would never show up. To
    pick it up, the annotation is evaluated afresh from the class that declared it.

    The annotation's original *source* is re-evaluated rather than its type structure being
    walked, so an alias nested in any container (`list[...]`, `dict[str, ...]`, `X | None`,
    and any combination) is handled without a case per container kind.

    The annotation is evaluated against the declaring module's globals, so an alias field
    on a settings class defined *inside a function* cannot also reference a name local to
    that function. That combination raises rather than silently going stale, and does not
    occur for module-level settings classes - which is what a plugin declares.
    """
    for name in settings.model_fields:
        for klass in settings.__mro__:
            raw = klass.__dict__.get("__annotations__", {}).get(name)
            if raw is None:
                continue
            if isinstance(raw, str) and any(alias in raw for alias in aliases):
                settings.model_fields[name].annotation = eval(raw, vars(sys.modules[klass.__module__]))  # noqa: S307
            break


class FromSettingsMixin:
    def __init_subclass__(
        cls: type[FromSettingsMixin],
        settings: type[BaseSettingsModel] | None = None,
        **kwargs,
    ):
        super().__init_subclass__(**kwargs)
        # Not every subclass needs to be creatable from settings (e.g. test doubles).
        # If no settings model is provided, skip registration.
        if settings is None:
            return

        if "_registry" not in cls.__dict__:
            cls._registry = {}

        settings._model = cls  # wire settings -> class

        field = settings.model_fields["type"]
        type_name = field.default
        if not isinstance(type_name, str) or not type_name:
            raise TypeError(f"{settings.__name__}.type must have a non-empty string default value for registration")

        for base in cls.__mro__:
            if "_registry" in base.__dict__:
                registry = base.__dict__["_registry"]
                if isinstance(registry, dict):
                    if type_name in registry:
                        raise TypeError(f"Duplicate registration for type {type_name!r}")
                    registry[type_name] = settings

        if settings not in _registered_settings:
            _registered_settings.append(settings)

    @classmethod
    def create(cls: type[FromSettingsMixin], data: dict[str, Any]):
        finalize()

        type_name = data.get("type")
        if not isinstance(type_name, str):
            raise ValueError("Missing or invalid 'type' in settings data")

        try:
            settings_model = cls._registry[type_name]
        except KeyError as exc:
            available = ", ".join(sorted(cls._registry.keys()))
            raise ValueError(f"Unknown type {type_name!r}. Available: {available}") from exc

        settings = settings_model.model_validate(data)
        return settings.convert()
