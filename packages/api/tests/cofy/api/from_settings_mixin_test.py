from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

import pytest
from pydantic import TypeAdapter, ValidationError

from cofy.api.from_settings_mixin import BaseSettingsModel, FromSettingsMixin, finalize


def test_classes_register_as_tree():
    class ASettings(BaseSettingsModel):
        type: Literal["a"] = "a"

    class A(FromSettingsMixin, settings=ASettings):
        pass

    class BSettings(BaseSettingsModel):
        type: Literal["b"] = "b"

    class B(A, settings=BSettings):
        pass

    class CSettings(BaseSettingsModel):
        type: Literal["c"] = "c"

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
        type: Literal["a"] = "a"
        foo: str

    class A(FromSettingsMixin, settings=ASettings):
        def __init__(self, foo: str):
            self.foo = foo

    class BSettings(ASettings):
        type: Literal["b"] = "b"
        bar: int

    class B(A, settings=BSettings):
        def __init__(self, foo: str, bar: int):
            super().__init__(foo)
            self.bar = bar * 2

    class CSettings(BaseSettingsModel):
        type: Literal["c"] = "c"
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
        type: Literal["a"] = "a"

    class A(FromSettingsMixin, settings=ASettings):
        pass

    class BSettings(BaseSettingsModel):
        type: Literal["b"] = "b"

    class B(FromSettingsMixin, settings=BSettings):
        pass

    assert A._registry == {"a": ASettings}
    assert B._registry == {"b": BSettings}

    pytest.raises(ValueError, lambda: A.create({"type": "b"}))
    pytest.raises(ValueError, lambda: B.create({"type": "a"}))


def test_settings_can_contain_settings():
    class InnerSettings(BaseSettingsModel):
        type: Literal["inner"] = "inner"
        value: int

    class Inner(FromSettingsMixin, settings=InnerSettings):
        def __init__(self, value: int):
            self.value = value

    class OuterSettings(BaseSettingsModel):
        type: Literal["outer"] = "outer"
        inner: InnerSettings

    class Outer(FromSettingsMixin, settings=OuterSettings):
        def __init__(self, inner: InnerSettings):
            self.inner = inner

    outer = Outer.create({"type": "outer", "inner": {"type": "inner", "value": 42}})
    assert isinstance(outer, Outer)
    assert isinstance(outer.inner, Inner)
    assert outer.inner.value == 42


def test_settings_convert_recurses_into_lists_and_dicts():
    class ChildSettings(BaseSettingsModel):
        type: Literal["child"] = "child"
        value: int

    class Child(FromSettingsMixin, settings=ChildSettings):
        def __init__(self, value: int):
            self.value = value

    class ParentSettings(BaseSettingsModel):
        type: Literal["parent"] = "parent"
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


def test_create_requires_string_type():
    class ASettings(BaseSettingsModel):
        type: Literal["a"] = "a"

    class A(FromSettingsMixin, settings=ASettings):
        pass

    with pytest.raises(ValueError, match="Missing or invalid 'type'"):
        A.create({})

    with pytest.raises(ValueError, match="Missing or invalid 'type'"):
        A.create({"type": 1})


def test_unknown_type_error_lists_available_types():
    class ASettings(BaseSettingsModel):
        type: Literal["a"] = "a"

    class A(FromSettingsMixin, settings=ASettings):
        pass

    class BSettings(BaseSettingsModel):
        type: Literal["b"] = "b"

    class B(A, settings=BSettings):
        pass

    with pytest.raises(ValueError, match=r"Unknown type"):
        A.create({"type": "missing"})


def test_subclass_without_settings_is_not_registered():
    class ASettings(BaseSettingsModel):
        type: Literal["a"] = "a"

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
        type: Literal["dup_a"] = "dup_a"

    class A(FromSettingsMixin, settings=ASettings):
        pass

    with pytest.raises(TypeError, match="Duplicate registration for type 'dup_a'"):

        class DuplicateASettings(BaseSettingsModel):
            type: Literal["dup_a"] = "dup_a"

        class DuplicateA(A, settings=DuplicateASettings):
            pass


def test_union_type_dispatches_on_type_tag():
    """The union returned by union_type() validates a payload as the subtype its `type`
    names, keeping that subtype's own fields."""

    class ASettings(BaseSettingsModel):
        type: Literal["a"] = "a"
        value: int

    class A(FromSettingsMixin, settings=ASettings):
        def __init__(self, value: int):
            self.value = value

    class BSettings(ASettings):
        type: Literal["b"] = "b"
        extra: str

    class B(A, settings=BSettings):
        def __init__(self, value: int, extra: str):
            super().__init__(value)
            self.extra = extra

    ta = TypeAdapter(ASettings.union_type())

    b = ta.validate_python({"type": "b", "value": 10, "extra": "hello"})
    assert isinstance(b, BSettings)
    assert b.extra == "hello"

    a = ta.validate_python({"type": "a", "value": 5})
    assert isinstance(a, ASettings)
    assert a.value == 5


def test_union_type_round_trips_subtype_fields():
    """Serialization keeps the fields of the matched subtype - no extra flags needed."""

    class PartSettings(BaseSettingsModel):
        type: Literal["part"] = "part"
        weight: int

    class Part(FromSettingsMixin, settings=PartSettings):
        def __init__(self, weight: int):
            self.weight = weight

    class HeavyPartSettings(PartSettings):
        type: Literal["heavy_part"] = "heavy_part"
        material: str

    class HeavyPart(Part, settings=HeavyPartSettings):
        def __init__(self, weight: int, material: str):
            super().__init__(weight)
            self.material = material

    ta = TypeAdapter(PartSettings.union_type())
    part = ta.validate_python({"type": "heavy_part", "weight": 10, "material": "steel"})

    assert ta.dump_python(part) == {"type": "heavy_part", "weight": 10, "material": "steel"}


def test_union_type_rejects_unregistered_type():
    """An unknown `type` must fail validation, rather than silently validating as the base
    model and dropping the payload's other fields."""

    class ASettings(BaseSettingsModel):
        type: Literal["known_a"] = "known_a"

    class A(FromSettingsMixin, settings=ASettings):
        pass

    class BSettings(BaseSettingsModel):
        type: Literal["known_b"] = "known_b"

    class B(A, settings=BSettings):
        pass

    ta = TypeAdapter(ASettings.union_type())

    with pytest.raises(ValidationError) as exc:
        ta.validate_python({"type": "not_registered", "source": {"api_key": "secret"}})

    assert "not_registered" in str(exc.value)


def test_union_type_schema_carries_discriminator():
    """The generated schema must describe the tag and which subtype each value maps to -
    this is what a spec-driven client (e.g. a form builder) reads."""

    class ShapeSettings(BaseSettingsModel):
        type: Literal["shape"] = "shape"

    class Shape(FromSettingsMixin, settings=ShapeSettings):
        pass

    class CircleSettings(ShapeSettings):
        type: Literal["circle"] = "circle"
        radius: float

    class Circle(Shape, settings=CircleSettings):
        def __init__(self, radius: float):
            self.radius = radius

    schema = TypeAdapter(ShapeSettings.union_type()).json_schema()

    assert schema["discriminator"]["propertyName"] == "type"
    assert set(schema["discriminator"]["mapping"]) == {"shape", "circle"}
    assert schema["$defs"]["CircleSettings"]["properties"]["radius"]["type"] == "number"


# --- finalize() and self-composing settings ---------------------------------------------
# Defined at module level so finalize() can publish the union alias into this module, the
# same way it does for a plugin module.


class NodeSettings(BaseSettingsModel):
    type: Literal["fsm_node"] = "fsm_node"


class Node(FromSettingsMixin, settings=NodeSettings):
    pass


if TYPE_CHECKING:
    # Published at runtime by finalize(); the base class is the static stand-in.
    AnyNodeSettings = NodeSettings


class WrapperSettings(NodeSettings):
    type: Literal["fsm_wrapper"] = "fsm_wrapper"
    label: str
    inner: AnyNodeSettings


class Wrapper(Node, settings=WrapperSettings):
    def __init__(self, label: str, inner: Node):
        self.label = label
        self.inner = inner


def test_union_alias_name_is_derived_from_the_settings_class():
    assert NodeSettings.union_alias() == "AnyNodeSettings"
    assert WrapperSettings.union_alias() == "AnyWrapperSettings"


def test_a_type_registered_after_resolution_is_picked_up():
    """Registration can continue after the unions have already been resolved once - a
    plugin imported late, or a test double defined in a test module. The alias fields must
    be re-resolved, or the newcomer would be missing from every union that should offer it
    and would fail validation as an unknown tag.

    Uses its own registry so it doesn't add a type to the one other tests assert on.
    """

    class RootSettings(BaseSettingsModel):
        type: Literal["late_root"] = "late_root"

    class Root(FromSettingsMixin, settings=RootSettings):
        pass

    if TYPE_CHECKING:
        AnyRootSettings = RootSettings

    class HolderSettings(RootSettings):
        type: Literal["late_holder"] = "late_holder"
        # dangling alias, published by finalize() into this test module
        held: AnyRootSettings

    class Holder(Root, settings=HolderSettings):
        def __init__(self, held: Root):
            self.held = held

    # resolve once, before the late type exists
    assert "late_extra" not in str(TypeAdapter(RootSettings.union_type()).json_schema())

    class LateSettings(RootSettings):
        type: Literal["late_extra"] = "late_extra"
        extra: int = 0

    class Late(Root, settings=LateSettings):
        def __init__(self, extra: int = 0):
            self.extra = extra

    # the nested alias field must accept the newcomer, not just the top level
    result = TypeAdapter(RootSettings.union_type()).validate_python(
        {"type": "late_holder", "held": {"type": "late_extra", "extra": 7}}
    )

    assert isinstance(result.held, LateSettings)
    assert result.held.extra == 7


def test_late_registration_reaches_aliases_inside_containers_and_inherited_fields():
    """Re-resolution re-evaluates a field's original annotation *source*, rather than
    walking the type structure, so an alias nested in any container is picked up without
    needing a case per container kind. Inherited fields resolve against the class that
    declared them."""

    class ItemSettings(BaseSettingsModel):
        type: Literal["ct_item"] = "ct_item"

    class Item(FromSettingsMixin, settings=ItemSettings):
        pass

    if TYPE_CHECKING:
        AnyItemSettings = ItemSettings

    class BoxSettings(ItemSettings):
        type: Literal["ct_box"] = "ct_box"
        one: AnyItemSettings
        many: list[AnyItemSettings] = []
        mapping: dict[str, AnyItemSettings] = {}
        maybe: AnyItemSettings | None = None
        deep: list[dict[str, AnyItemSettings]] = []

    class Box(Item, settings=BoxSettings):
        def __init__(self, **kwargs):
            pass

    class ChildBoxSettings(BoxSettings):  # inherits every alias field above
        type: Literal["ct_child_box"] = "ct_child_box"

    class ChildBox(Box, settings=ChildBoxSettings):
        def __init__(self, **kwargs):
            pass

    TypeAdapter(ItemSettings.union_type()).json_schema()  # resolve before the late type exists

    class LateSettings(ItemSettings):
        type: Literal["ct_late"] = "ct_late"
        n: int = 0

    class Late(Item, settings=LateSettings):
        def __init__(self, n: int = 0):
            pass

    ta = TypeAdapter(ItemSettings.union_type())
    late = {"type": "ct_late", "n": 7}

    for tag in ("ct_box", "ct_child_box"):
        box = ta.validate_python(
            {"type": tag, "one": late, "many": [late], "mapping": {"k": late}, "maybe": late, "deep": [{"k": late}]}
        )
        assert isinstance(box.one, LateSettings)
        assert isinstance(box.many[0], LateSettings)
        assert isinstance(box.mapping["k"], LateSettings)
        assert isinstance(box.maybe, LateSettings)
        assert isinstance(box.deep[0]["k"], LateSettings)

    items = ta.json_schema()["$defs"]["BoxSettings"]["properties"]["many"]["items"]
    assert "ct_late" in items["discriminator"]["mapping"]


def test_finalize_resolves_dangling_union_annotations():
    """A field annotated with an as-yet-unbound `Any<Name>` is left unresolved until
    finalize() publishes the union - after which it validates polymorphically."""
    finalize()

    ta = TypeAdapter(NodeSettings.union_type())
    result = ta.validate_python(
        {
            "type": "fsm_wrapper",
            "label": "outer",
            "inner": {"type": "fsm_wrapper", "label": "inner", "inner": {"type": "fsm_node"}},
        }
    )

    assert isinstance(result, WrapperSettings)
    assert isinstance(result.inner, WrapperSettings)
    assert isinstance(result.inner.inner, NodeSettings)
    assert result.inner.label == "inner"


def test_self_composing_settings_round_trip_at_every_depth():
    """A settings type that composes another instance of itself must survive a full
    round trip with every level's own fields intact."""
    finalize()

    ta = TypeAdapter(NodeSettings.union_type())
    payload = {
        "type": "fsm_wrapper",
        "label": "outer",
        "inner": {"type": "fsm_wrapper", "label": "inner", "inner": {"type": "fsm_node"}},
    }

    assert ta.dump_python(ta.validate_python(payload)) == payload


def test_self_composing_settings_schema_is_correct_at_every_usage_site():
    """The recursive field must advertise the full set of subtypes wherever it appears -
    a client reading the schema has to know it can recurse at any depth."""
    finalize()

    schema = TypeAdapter(NodeSettings.union_type()).json_schema()
    inner = schema["$defs"]["WrapperSettings"]["properties"]["inner"]

    assert set(inner["discriminator"]["mapping"]) == {"fsm_node", "fsm_wrapper"}
    # and it refers back to the wrapper itself, rather than only to the plain base type
    assert inner["discriminator"]["mapping"]["fsm_wrapper"].endswith("/WrapperSettings")


def test_abstract_types_are_pruned_from_the_registry():
    """A base that only exists to be subclassed must not be offered as a usable type."""
    from abc import ABC, abstractmethod

    class ShapeSettings(BaseSettingsModel):
        type: Literal["cr_shape"] = "cr_shape"

    class Shape(FromSettingsMixin, ABC, settings=ShapeSettings):
        @abstractmethod
        def area(self) -> float:
            """Area of the shape."""

    class SquareSettings(ShapeSettings):
        type: Literal["cr_square"] = "cr_square"
        side: float = 1.0

    class Square(Shape, settings=SquareSettings):
        def __init__(self, side: float = 1.0):
            self.side = side

        def area(self) -> float:
            return self.side**2

    finalize()

    assert set(Shape._registry) == {"cr_square"}
    assert Shape._registry["cr_square"] is SquareSettings


def test_a_config_naming_an_abstract_type_fails_validation():
    """Rather than validating and then raising when something tries to build it."""
    from abc import ABC, abstractmethod

    class ToolSettings(BaseSettingsModel):
        type: Literal["pr_tool"] = "pr_tool"

    class Tool(FromSettingsMixin, ABC, settings=ToolSettings):
        @abstractmethod
        def use(self) -> str:
            """Use the tool."""

    class HammerSettings(ToolSettings):
        type: Literal["pr_hammer"] = "pr_hammer"

    class Hammer(Tool, settings=HammerSettings):
        def use(self) -> str:
            return "bang"

    ta = TypeAdapter(ToolSettings.union_type())

    assert isinstance(ta.validate_python({"type": "pr_hammer"}), HammerSettings)
    with pytest.raises(ValidationError):
        ta.validate_python({"type": "pr_tool"})


def test_only_unimplemented_types_are_pruned_not_every_abstract_descendant():
    """Having an abstract ancestor is fine; having an unimplemented method is not."""
    from abc import ABC, abstractmethod

    class DeviceSettings(BaseSettingsModel):
        type: Literal["pr_device"] = "pr_device"

    class Device(FromSettingsMixin, ABC, settings=DeviceSettings):
        @abstractmethod
        def run(self) -> str:
            """Run the device."""

    class PartialSettings(DeviceSettings):
        type: Literal["pr_partial"] = "pr_partial"

    class Partial(Device, settings=PartialSettings):
        pass  # still abstract: `run` is not implemented

    class DoneSettings(PartialSettings):
        type: Literal["pr_done"] = "pr_done"

    class Done(Partial, settings=DoneSettings):
        def run(self) -> str:
            return "running"

    finalize()

    assert set(Device._registry) == {"pr_done"}


def test_registry_exposes_the_registered_types():
    class ColourSettings(BaseSettingsModel):
        type: Literal["reg_colour"] = "reg_colour"

    class Colour(FromSettingsMixin, settings=ColourSettings):
        pass

    class RedSettings(ColourSettings):
        type: Literal["reg_red"] = "reg_red"

    class Red(Colour, settings=RedSettings):
        pass

    assert ColourSettings.registry() == {"reg_colour": ColourSettings, "reg_red": RedSettings}


def test_registry_returns_a_copy_callers_cannot_corrupt():
    class SizeSettings(BaseSettingsModel):
        type: Literal["reg_size"] = "reg_size"

    class Size(FromSettingsMixin, settings=SizeSettings):
        pass

    SizeSettings.registry().clear()

    assert SizeSettings.registry() == {"reg_size": SizeSettings}


def test_an_abstract_base_with_no_implementations_stays_registered_with_a_warning(
    caplog: pytest.LogCaptureFixture,
):
    """Removing it would leave a union with no members at all, which cannot be expressed and
    would break every model with a field of that type. Keeping it is a workaround for a
    family that has nothing configurable in it, so it must not pass silently."""
    from abc import ABC, abstractmethod

    class LonelySettings(BaseSettingsModel):
        type: Literal["pr_lonely"] = "pr_lonely"

    class Lonely(FromSettingsMixin, ABC, settings=LonelySettings):
        @abstractmethod
        def act(self) -> str:
            """Do something."""

    with caplog.at_level(logging.WARNING, logger="cofy.api.from_settings_mixin"):
        finalize(force=True)

    assert set(Lonely._registry) == {"pr_lonely"}
    assert LonelySettings.union_type() is not None
    warnings = [r.getMessage() for r in caplog.records]
    assert any("pr_lonely" in w and "Lonely" in w for w in warnings), warnings


def test_pruning_a_family_that_has_implementations_warns_about_nothing(caplog: pytest.LogCaptureFixture):
    from abc import ABC, abstractmethod

    class PairSettings(BaseSettingsModel):
        type: Literal["pr_pair"] = "pr_pair"

    class Pair(FromSettingsMixin, ABC, settings=PairSettings):
        @abstractmethod
        def act(self) -> str:
            """Do something."""

    class RealSettings(PairSettings):
        type: Literal["pr_real"] = "pr_real"

    class Real(Pair, settings=RealSettings):
        def act(self) -> str:
            return "acted"

    with caplog.at_level(logging.WARNING, logger="cofy.api.from_settings_mixin"):
        finalize(force=True)

    assert set(Pair._registry) == {"pr_real"}
    assert not [r for r in caplog.records if "pr_pair" in r.getMessage()]
