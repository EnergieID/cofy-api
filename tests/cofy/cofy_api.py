from fastapi import FastAPI

from src.cofy.cofy_api import CofyApi
from tests.cofy.dummy_module import DummyModule


def test_cofy_initialization():
    settings = {"title": "Test API", "version": "1.2.3", "description": "Test desc"}
    cofy = CofyApi(**settings)
    assert isinstance(cofy, FastAPI)
    assert cofy.title == "Test API"
    assert cofy.version == "1.2.3"
    assert cofy.description == "Test desc"
    assert isinstance(cofy._modulesRouter, object)


def test_register_and_get_module():
    cofy = CofyApi()
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
    cofy = CofyApi()
    assert cofy.get_module("missing", "none") is None
    assert cofy.get_modules_by_type("missing") == {}


def test_modules_with_same_name_overwrite():
    cofy = CofyApi()
    module1 = DummyModule(name="sameName", type_="typeX")
    cofy.register_module(module1)
    assert cofy.get_module("typeX", "sameName") is module1

    module2 = DummyModule(name="sameName", type_="typeX")
    cofy.register_module(module2)
    assert cofy.get_module("typeX", "sameName") is module2
    assert cofy.get_modules_by_type("typeX") == {"sameName": module2}
