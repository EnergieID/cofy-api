from __future__ import annotations

import pytest

from cofy.api.from_settings_mixin import BaseSettingsModel, FromSettingsMixin


def test_union_type_skips_unregistered_nested_settings():
    """A BaseSettingsModel subclass used as a field type but never registered with a
    FromSettingsMixin is left as-is in the response schema (not expanded into a union)."""

    class MetadataSettings(BaseSettingsModel):
        type: str = "metadata"
        label: str

    # MetadataSettings intentionally has no FromSettingsMixin subclass registered.

    class WidgetSettings(BaseSettingsModel):
        type: str = "widget"
        meta: MetadataSettings

    class Widget(FromSettingsMixin, settings=WidgetSettings):
        def __init__(self, meta: MetadataSettings):
            self.meta = meta

    union_type = WidgetSettings.union_type()

    from pydantic import TypeAdapter

    ta = TypeAdapter(union_type)
    result = ta.validate_python({"type": "widget", "meta": {"type": "metadata", "label": "hello"}})
    assert result.meta.label == "hello"


def test_classes_register_as_tree():
    class ASettings(BaseSettingsModel):
        type: str = "a"

    class A(FromSettingsMixin, settings=ASettings):
        pass

    class BSettings(BaseSettingsModel):
        type: str = "b"

    class B(A, settings=BSettings):
        pass

    class CSettings(BaseSettingsModel):
        type: str = "c"

    class C(A, settings=CSettings):
        pass

    assert A._registry == {"a": ASettings, "b": BSettings, "c": CSettings}
    assert B._registry == {"b": BSettings}
    assert C._registry == {"c": CSettings}

    a = A.create({"type": "a"})
    b = A.create({"type": "b"})
    c = A.create({"type": "c"})

    assert isinstance(a, A)
    assert isinstance(b, B)
    assert isinstance(c, C)


def test_can_use_differing_settings():
    class ASettings(BaseSettingsModel):
        type: str = "a"
        foo: str

    class A(FromSettingsMixin, settings=ASettings):
        def __init__(self, foo: str):
            self.foo = foo

    class BSettings(ASettings):
        type: str = "b"
        bar: int

    class B(A, settings=BSettings):
        def __init__(self, foo: str, bar: int):
            super().__init__(foo)
            self.bar = bar * 2

    class CSettings(BaseSettingsModel):
        type: str = "c"
        bar: int

    class C(A, settings=CSettings):
        def __init__(self, bar: int):
            super().__init__("C-foo")
            self.bar = bar * 3

    a = A.create({"type": "a", "foo": "hello"})
    b = A.create({"type": "b", "foo": "world", "bar": 21})
    c = A.create({"type": "c", "bar": 21})

    assert isinstance(a, A)
    assert isinstance(b, B)
    assert isinstance(c, C)
    assert a.foo == "hello"
    assert b.foo == "world"
    assert b.bar == 42
    assert c.foo == "C-foo"
    assert c.bar == 63


def test_no_overlap_in_different_registries():
    class ASettings(BaseSettingsModel):
        type: str = "a"

    class A(FromSettingsMixin, settings=ASettings):
        pass

    class BSettings(BaseSettingsModel):
        type: str = "b"

    class B(FromSettingsMixin, settings=BSettings):
        pass

    assert A._registry == {"a": ASettings}
    assert B._registry == {"b": BSettings}

    pytest.raises(ValueError, lambda: A.create({"type": "b"}))
    pytest.raises(ValueError, lambda: B.create({"type": "a"}))


def test_settings_can_contain_settings():
    class InnerSettings(BaseSettingsModel):
        type: str = "inner"
        value: int

    class Inner(FromSettingsMixin, settings=InnerSettings):
        def __init__(self, value: int):
            self.value = value

    class OuterSettings(BaseSettingsModel):
        type: str = "outer"
        inner: InnerSettings

    class Outer(FromSettingsMixin, settings=OuterSettings):
        def __init__(self, inner: InnerSettings):
            self.inner = inner

    outer = Outer.create({"type": "outer", "inner": {"type": "inner", "value": 42}})
    assert isinstance(outer, Outer)
    assert isinstance(outer.inner, Inner)
    assert outer.inner.value == 42


def test_recursion_in_inner_settings():
    class ASettings(BaseSettingsModel):
        type: str = "a"
        foo: int

    class A(FromSettingsMixin, settings=ASettings):
        def __init__(self, foo: int):
            self.foo = foo

    class BSettings(ASettings):
        type: str = "b"
        a: ASettings

    class B(A, settings=BSettings):
        def __init__(self, a: A, foo: int):
            self.a = a
            super().__init__(foo)

    b = B.create({"type": "b", "foo": 10, "a": {"type": "b", "foo": 20, "a": {"type": "a", "foo": 30}}})
    assert isinstance(b, B)
    assert isinstance(b.a, B)
    assert isinstance(b.a.a, A)
    assert b.foo == 10
    assert b.a.foo == 20
    assert b.a.a.foo == 30


def test_settings_dispatch_accepts_existing_settings_instance():
    class ChildSettings(BaseSettingsModel):
        type: str = "child"
        value: int

    class Child(FromSettingsMixin, settings=ChildSettings):
        def __init__(self, value: int):
            self.value = value

    class ParentSettings(BaseSettingsModel):
        type: str = "parent"
        child: ChildSettings

    class Parent(FromSettingsMixin, settings=ParentSettings):
        def __init__(self, child: Child):
            self.child = child

    child_settings = ChildSettings(value=42)
    parent = Parent.create({"type": "parent", "child": child_settings})

    assert isinstance(parent, Parent)
    assert isinstance(parent.child, Child)
    assert parent.child.value == 42


def test_settings_convert_recurses_into_lists_and_dicts():
    class ChildSettings(BaseSettingsModel):
        type: str = "child"
        value: int

    class Child(FromSettingsMixin, settings=ChildSettings):
        def __init__(self, value: int):
            self.value = value

    class ParentSettings(BaseSettingsModel):
        type: str = "parent"
        items: list[ChildSettings]
        mapping: dict[str, ChildSettings]

    class Parent(FromSettingsMixin, settings=ParentSettings):
        def __init__(self, items: list[Child], mapping: dict[str, Child]):
            self.items = items
            self.mapping = mapping

    parent = Parent.create(
        {
            "type": "parent",
            "items": [{"type": "child", "value": 1}, {"type": "child", "value": 2}],
            "mapping": {"left": {"type": "child", "value": 3}},
        }
    )

    assert [item.value for item in parent.items] == [1, 2]
    assert parent.mapping["left"].value == 3


def test_settings_dispatch_falls_back_for_non_dict_values():
    class NumberSettings(BaseSettingsModel):
        type: str = "number"
        value: int

    parsed = NumberSettings.model_validate({"type": "number", "value": 7})

    assert parsed.value == 7


def test_create_requires_string_type():
    class ASettings(BaseSettingsModel):
        type: str = "a"

    class A(FromSettingsMixin, settings=ASettings):
        pass

    with pytest.raises(ValueError, match="Missing or invalid 'type'"):
        A.create({})

    with pytest.raises(ValueError, match="Missing or invalid 'type'"):
        A.create({"type": 1})


def test_unknown_type_error_lists_available_types():
    class ASettings(BaseSettingsModel):
        type: str = "a"

    class A(FromSettingsMixin, settings=ASettings):
        pass

    class BSettings(BaseSettingsModel):
        type: str = "b"

    class B(A, settings=BSettings):
        pass

    with pytest.raises(ValueError, match=r"Unknown type"):
        A.create({"type": "missing"})


def test_subclass_without_settings_is_not_registered():
    class ASettings(BaseSettingsModel):
        type: str = "a"

    class A(FromSettingsMixin, settings=ASettings):
        pass

    class Unregistered(A):
        pass

    assert A._registry == {"a": ASettings}
    assert "_registry" not in Unregistered.__dict__


def test_rejects_empty_type_default():
    with pytest.raises(TypeError, match="non-empty string default value"):

        class EmptyTypeSettings(BaseSettingsModel):
            type: str = ""

        class EmptyTypeConsumer(FromSettingsMixin, settings=EmptyTypeSettings):
            pass


def test_rejects_duplicate_type_registration():
    class ASettings(BaseSettingsModel):
        type: str = "a"

    class A(FromSettingsMixin, settings=ASettings):
        pass

    with pytest.raises(TypeError, match="Duplicate registration for type 'a'"):

        class DuplicateASettings(BaseSettingsModel):
            type: str = "a"

        class DuplicateA(A, settings=DuplicateASettings):
            pass


def test_settings_classes_correctly_validate_subclasses():
    class ASettings(BaseSettingsModel):
        type: str = "a"
        value: int

    class A(FromSettingsMixin, settings=ASettings):
        def __init__(self, value: int):
            self.value = value

    class BSettings(ASettings):
        type: str = "b"
        extra: str

    class B(A, settings=BSettings):
        def __init__(self, value: int, extra: str):
            super().__init__(value)
            self.extra = extra

    b = ASettings.model_validate({"type": "b", "value": 10, "extra": "hello"})
    assert isinstance(b, BSettings)
    assert b.value == 10
    assert b.extra == "hello"


def test_settings_classes_correctly_validate_param_subclasses():
    class ASettings(BaseSettingsModel):
        type: str = "a"
        value: int

    class A(FromSettingsMixin, settings=ASettings):
        def __init__(self, value: int):
            self.value = value

    class BSettings(ASettings):
        type: str = "b"
        extra: str

    class B(A, settings=BSettings):
        def __init__(self, value: int, extra: str):
            super().__init__(value)
            self.extra = extra

    class CSettings(BaseSettingsModel):
        type: str = "c"
        a: ASettings

    class C(FromSettingsMixin, settings=CSettings):
        def __init__(self, a: A):
            self.a = a

    c = CSettings.model_validate({"type": "c", "a": {"type": "b", "value": 10, "extra": "hello"}})
    assert isinstance(c, CSettings)
    assert isinstance(c.a, BSettings)
    assert c.a.value == 10
    assert c.a.extra == "hello"

    c = CSettings.model_validate({"type": "c", "a": {"type": "a", "value": 5}})
    assert isinstance(c, CSettings)
    assert isinstance(c.a, ASettings)
    assert c.a.value == 5


def test_union_type_returns_correct_union():
    class ASettings(BaseSettingsModel):
        type: str = "a"
        value: int

    class A(FromSettingsMixin, settings=ASettings):
        def __init__(self, value: int):
            self.value = value

    class BSettings(ASettings):
        type: str = "b"
        extra: str

    class B(A, settings=BSettings):
        def __init__(self, value: int, extra: str):
            super().__init__(value)
            self.extra = extra

    class CSettings(BaseSettingsModel):
        type: str = "c"
        a: ASettings

    class C(FromSettingsMixin, settings=CSettings):
        def __init__(self, a: A):
            self.a = a

    union_type = CSettings.union_type()

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.get("/test", response_model=union_type)
    def test_endpoint():
        return {"type": "c", "a": {"type": "b", "value": 10, "extra": "hello"}}

    client = TestClient(app)
    response = client.get("/test")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "c"
    assert data["a"]["type"] == "b"
    assert data["a"]["value"] == 10
    assert data["a"]["extra"] == "hello"


def test_union_type_expands_list_fields():
    """union_type() recursively expands list[SettingsType] fields so response includes subtype-specific fields."""

    class PartSettings(BaseSettingsModel):
        type: str = "part"
        weight: int

    class Part(FromSettingsMixin, settings=PartSettings):
        def __init__(self, weight: int):
            self.weight = weight

    class HeavyPartSettings(PartSettings):
        type: str = "heavy_part"
        material: str

    class HeavyPart(Part, settings=HeavyPartSettings):
        def __init__(self, weight: int, material: str):
            super().__init__(weight)
            self.material = material

    class CrateSettings(BaseSettingsModel):
        type: str = "crate"
        parts: list[PartSettings]
        named_parts: dict[str, PartSettings] = {}
        labels: list[str] = []

    class Crate(FromSettingsMixin, settings=CrateSettings):
        def __init__(self, parts: list[Part], named_parts: dict[str, Part], labels: list[str]):
            self.parts = parts
            self.named_parts = named_parts
            self.labels = labels

    union_type = CrateSettings.union_type()

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.get("/crate", response_model=union_type)
    def endpoint():
        return {
            "type": "crate",
            "parts": [{"type": "heavy_part", "weight": 10, "material": "steel"}],
            "named_parts": {"main": {"type": "heavy_part", "weight": 5, "material": "iron"}},
            "labels": ["fragile"],
        }

    client = TestClient(app)
    response = client.get("/crate")
    assert response.status_code == 200
    data = response.json()
    assert data["parts"][0]["material"] == "steel"
    assert data["named_parts"]["main"]["material"] == "iron"
    assert data["labels"] == ["fragile"]


def test_union_type_expands_optional_fields():
    """union_type() recursively expands Optional[SettingsType] fields so response includes subtype-specific fields."""

    class EngineSettings(BaseSettingsModel):
        type: str = "engine"
        power: int

    class Engine(FromSettingsMixin, settings=EngineSettings):
        def __init__(self, power: int):
            self.power = power

    class TurboEngineSettings(EngineSettings):
        type: str = "turbo_engine"
        boost: float

    class TurboEngine(Engine, settings=TurboEngineSettings):
        def __init__(self, power: int, boost: float):
            super().__init__(power)
            self.boost = boost

    class CarSettings(BaseSettingsModel):
        type: str = "car"
        engine: EngineSettings | None = None

    class Car(FromSettingsMixin, settings=CarSettings):
        def __init__(self, engine: Engine | None = None):
            self.engine = engine

    union_type = CarSettings.union_type()

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.get("/car", response_model=union_type)
    def endpoint():
        return {"type": "car", "engine": {"type": "turbo_engine", "power": 200, "boost": 1.5}}

    client = TestClient(app)
    response = client.get("/car")
    assert response.status_code == 200
    data = response.json()
    assert data["engine"]["boost"] == 1.5
