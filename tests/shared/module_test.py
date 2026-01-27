import pytest

from src.shared.module import Module


class DummyCofy:
    pass


class DummyModule(Module):
    def __init__(self, settings):
        super().__init__(settings)
        self._type = "dummy"

    def init_routes(self):
        pass

    @property
    def type(self):
        return self._type


def test_module_name_default():
    m = DummyModule({})
    assert m.name == "default"


def test_module_name_custom():
    m = DummyModule({"name": "custom_name"})
    assert m.name == "custom_name"


def test_module_metadata_default():
    m = DummyModule({})
    assert m.metadata == {}


def test_module_type():
    m = DummyModule({})
    assert m.type == "dummy"


def test_module_is_abstract():
    # Module should be abstract and not instantiable
    with pytest.raises(TypeError):
        Module({})
