from __future__ import annotations

from types import UnionType
from typing import Annotated, Any, ClassVar, Union, get_args, get_origin

from pydantic import BaseModel, Discriminator, Tag, create_model, model_validator


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
    def union_type(cls) -> Any:
        """Return a discriminated union type of registered settings models.
        Nested `BaseSettingsModel`-typed fields are expanded to their own discriminated unions
        """
        registry = getattr(cls._model, "_registry", {})
        if not registry:
            return cls

        response_cache: dict[type[BaseSettingsModel], type[BaseSettingsModel]] = {}
        stack: set[type[BaseSettingsModel]] = set()

        tagged_models: list[Any] = []
        for key, model in registry.items():
            resolved_model = _build_recursive_response_model(model, response_cache, stack)
            tagged_models.append(Annotated[resolved_model, Tag(key)])  # ty: ignore[invalid-type-form]

        union = _build_union_type(tagged_models)
        return Annotated[union, Discriminator(_discriminator_type)]


def _discriminator_type(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("type")
    return getattr(value, "type", None)


def _build_union_type(models: list[Any]) -> Any:
    if not models:
        return Any

    union = models[0]
    for model in models[1:]:
        union = union | model
    return union


def _build_recursive_response_model(
    model: type[BaseSettingsModel],
    cache: dict[type[BaseSettingsModel], type[BaseSettingsModel]],
    stack: set[type[BaseSettingsModel]],
) -> type[BaseSettingsModel]:
    if model in cache:
        return cache[model]

    if model in stack:
        # Break circular references by falling back to the current model.
        return model

    stack.add(model)
    overrides: dict[str, tuple[Any, Any]] = {}

    for field_name, field in model.model_fields.items():
        new_annotation = _transform_annotation(field.annotation, cache, stack)
        if new_annotation is field.annotation:
            continue

        default = ... if field.is_required() else field.default
        overrides[field_name] = (new_annotation, default)
        default = ... if field.is_required() else field.default
        overrides[field_name] = (new_annotation, default)

    stack.remove(model)

    if not overrides:
        cache[model] = model
        return model

    recursive_model = create_model(
        f"{model.__name__}Response",
        __base__=model,
        __module__=model.__module__,
        **overrides,
    )  # ty: ignore[no-matching-overload]
    cache[model] = recursive_model
    return recursive_model


def _transform_annotation(
    annotation: Any,
    cache: dict[type[BaseSettingsModel], type[BaseSettingsModel]],
    stack: set[type[BaseSettingsModel]],
) -> Any:
    if isinstance(annotation, type) and issubclass(annotation, BaseSettingsModel):
        model_cls = getattr(annotation, "_model", None)
        if model_cls is None:
            return annotation
        return annotation.union_type()

    origin = get_origin(annotation)
    if origin is None:
        return annotation

    args = get_args(annotation)
    if not args:
        return annotation

    if origin is Annotated:
        transformed = _transform_annotation(args[0], cache, stack)
        if transformed is args[0]:
            return annotation
        return Annotated[transformed, *args[1:]]

    transformed_args = tuple(_transform_annotation(arg, cache, stack) for arg in args)
    if transformed_args == args:
        return annotation

    if origin in (Union, UnionType):
        union = transformed_args[0]
        for arg in transformed_args[1:]:
            union = union | arg
        return union

    try:
        if len(transformed_args) == 1:
            return origin[transformed_args[0]]
        return origin[transformed_args]
    except Exception:
        return annotation


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
