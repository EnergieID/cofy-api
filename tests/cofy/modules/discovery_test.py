from __future__ import annotations

import logging
from types import SimpleNamespace

from cofy.modules import discovery


def test_discover_installed_types_imports_each_top_level_submodule(monkeypatch):
    imported = []

    monkeypatch.setattr(
        discovery.pkgutil,
        "iter_modules",
        lambda *args, **kwargs: iter(
            [SimpleNamespace(name="cofy.modules.fake_a"), SimpleNamespace(name="cofy.modules.fake_b")]
        ),
    )
    monkeypatch.setattr(discovery.importlib, "import_module", imported.append)

    discovery.discover_installed_types()

    assert imported == ["cofy.modules.fake_a", "cofy.modules.fake_b"]


def test_discover_installed_types_skips_module_with_missing_optional_dependency(monkeypatch, caplog):
    """A submodule whose own third-party dependency isn't installed (e.g. a tariff source
    importing `entsoe`) must not abort discovery of the rest."""
    imported = []

    def fake_import_module(name: str) -> None:
        if name == "cofy.modules.fake_missing_dep":
            raise ImportError("No module named 'third_party_lib'")
        imported.append(name)

    monkeypatch.setattr(
        discovery.pkgutil,
        "iter_modules",
        lambda *args, **kwargs: iter(
            [
                SimpleNamespace(name="cofy.modules.fake_missing_dep"),
                SimpleNamespace(name="cofy.modules.fake_ok"),
            ]
        ),
    )
    monkeypatch.setattr(discovery.importlib, "import_module", fake_import_module)

    with caplog.at_level(logging.DEBUG, logger=discovery.logger.name):
        discovery.discover_installed_types()  # must not raise

    assert imported == ["cofy.modules.fake_ok"]  # discovery continued past the failure
    assert "cofy.modules.fake_missing_dep" in caplog.text


def test_discover_plugin_types_loads_every_registered_entry_point(monkeypatch):
    loaded = []

    class FakeEntryPoint:
        def __init__(self, name: str):
            self.name = name
            self.value = f"acme_energy.modules:{name}"

        def load(self):
            loaded.append(self.name)

    entry_points = [FakeEntryPoint("plugin_a"), FakeEntryPoint("plugin_b")]

    def fake_entry_points(*, group: str):
        assert group == discovery.ENTRY_POINT_GROUP
        return entry_points

    monkeypatch.setattr(discovery, "entry_points", fake_entry_points)

    discovery.discover_plugin_types()

    assert loaded == ["plugin_a", "plugin_b"]


def test_discover_plugin_types_logs_and_continues_when_a_plugin_fails_to_load(monkeypatch, caplog):
    """A third-party plugin missing its own dependency must not stop other plugins from
    loading, and the failure must be surfaced rather than silently swallowed."""
    loaded = []

    class BrokenEntryPoint:
        name = "plugin_broken"
        value = "acme_energy.modules:BrokenModule"

        def load(self):
            raise ImportError("missing dependency 'acme_energy'")

    class OkEntryPoint:
        name = "plugin_ok"
        value = "acme_energy.modules:OkModule"

        def load(self):
            loaded.append(self.name)

    monkeypatch.setattr(discovery, "entry_points", lambda *, group: [BrokenEntryPoint(), OkEntryPoint()])

    with caplog.at_level(logging.WARNING, logger=discovery.logger.name):
        discovery.discover_plugin_types()  # must not raise

    assert loaded == ["plugin_ok"]  # discovery continued past the failure
    assert "plugin_broken" in caplog.text


def test_discover_all_types_runs_both_installed_and_plugin_discovery(monkeypatch):
    calls = []

    monkeypatch.setattr(discovery, "discover_installed_types", lambda: calls.append("installed"))
    monkeypatch.setattr(discovery, "discover_plugin_types", lambda: calls.append("plugin"))

    discovery.discover_all_types()

    assert calls == ["installed", "plugin"]
