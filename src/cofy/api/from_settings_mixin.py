from __future__ import annotations

from typing import Annotated, Any, ClassVar

from pydantic import BaseModel, Discriminator, Tag, model_validator


def _resolve(value: Any) -> Any:
    """Recursively convert any BaseSettingsModel instances to their actual objects."""
    if isinstance(value, BaseSettingsModel):
        return value.convert()
    if hasattr(value, "get_secret_value") and callable(value.get_secret_value):
        return value.get_secret_value()
    if isinstance(value, list):
        return [_resolve(v) for v in value]
    if isinstance(value, dict):
        return {_resolve(k): _resolve(v) for k, v in value.items()}
    return value


class BaseSettingsModel(BaseModel):
    _model: ClassVar[Any]  # wired automatically on registration

    @model_validator(mode="wrap")
    @classmethod
    def _polymorphic_dispatch(cls, value: Any, handler: Any) -> Any:
        if isinstance(value, BaseSettingsModel):
            return value

        if isinstance(value, dict):
            type_name = value.get("type")
            model_cls = getattr(cls, "_model", None)
            if isinstance(type_name, str) and model_cls is not None:
                registry = getattr(model_cls, "_registry", {})
                concrete_settings = registry.get(type_name)
                if concrete_settings is not None and concrete_settings is not cls:
                    return concrete_settings.model_validate(value)

        return handler(value)

    def convert(self) -> Any:
        kwargs = {name: _resolve(getattr(self, name)) for name in self.__class__.model_fields if name != "type"}
        return self._model(**kwargs)

    @classmethod
    def union_type(cls):
        """Return a union type of registered settings models."""
        registry = getattr(cls._model, "_registry", {})
        models = tuple(Annotated[model, Tag(key)] for key, model in registry.items())
        return Annotated[
            models, Discriminator(lambda x: x.get("type") if isinstance(x, dict) else getattr(x, "type", None))  # ty: ignore[invalid-type-form]
        ]  # noqa: UP007


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
                    if type_name in registry and registry[type_name].__name__ != settings.__name__:
                        raise TypeError(
                            f"Duplicate registration for type {type_name!r} in {cls.__name__} and {registry[type_name].__name__}"
                        )
                    registry[type_name] = settings

    @classmethod
    def create(cls: type[FromSettingsMixin], data: dict[str, Any]):
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
