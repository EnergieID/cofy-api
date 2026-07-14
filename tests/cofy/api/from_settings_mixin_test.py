import pytest
from pydantic import SecretStr

from cofy.api.from_settings_mixin import BaseSettingsModel, FromSettingsMixin


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
            self.bar = bar * 2

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
    assert c.bar == 42


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


def test_secret_values_are_unwrapped():
    class SecretSettings(BaseSettingsModel):
        type: str = "secret"
        token: SecretStr

    class SecretConsumer(FromSettingsMixin, settings=SecretSettings):
        def __init__(self, token: str):
            self.token = token

    consumer = SecretConsumer.create({"type": "secret", "token": "super-secret"})
    assert isinstance(consumer, SecretConsumer)
    assert isinstance(consumer.token, str)
    assert consumer.token == "super-secret"


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
