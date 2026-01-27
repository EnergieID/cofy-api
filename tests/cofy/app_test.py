from fastapi import FastAPI

from src.cofy.app import Cofy
from tests.cofy.dummy_module import DummyModule


def test_cofy_initialization():
    settings = {"title": "Test API", "version": "1.2.3", "description": "Test desc"}
    cofy = Cofy(settings)
    assert isinstance(cofy.fastApi, FastAPI)
    assert cofy.fastApi.title == "Test API"
    assert cofy.fastApi.version == "1.2.3"
    assert cofy.fastApi.description == "Test desc"
    assert isinstance(cofy.modulesRouter, object)
    assert cofy.settings == settings


def test_register_and_get_module():
    cofy = Cofy({})
    module = DummyModule(name="mod1", type_="typeA")
    cofy.register_module(module)
    assert module.cofy is cofy
    assert cofy.get_module("typeA", "mod1") is module
    assert cofy.get_modules_by_type("typeA") == {"mod1": module}

    # Register another module of same type
    module2 = DummyModule(name="mod2", type_="typeA")
    cofy.register_module(module2)
    assert cofy.get_module("typeA", "mod2") is module2
    assert set(cofy.get_modules_by_type("typeA").keys()) == {"mod1", "mod2"}

    # Register module of different type
    module3 = DummyModule(name="mod3", type_="typeB")
    cofy.register_module(module3)
    assert cofy.get_module("typeB", "mod3") is module3
    assert cofy.get_modules_by_type("typeB") == {"mod3": module3}


def test_get_module_returns_none_for_missing():
    cofy = Cofy({})
    assert cofy.get_module("missing", "none") is None
    assert cofy.get_modules_by_type("missing") == {}


def test_modules_with_same_name_overwrite():
    cofy = Cofy({})
    module1 = DummyModule(name="sameName", type_="typeX")
    cofy.register_module(module1)
    assert cofy.get_module("typeX", "sameName") is module1

    module2 = DummyModule(name="sameName", type_="typeX")
    cofy.register_module(module2)
    assert cofy.get_module("typeX", "sameName") is module2
    assert cofy.get_modules_by_type("typeX") == {"sameName": module2}
