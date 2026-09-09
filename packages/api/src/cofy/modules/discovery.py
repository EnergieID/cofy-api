from __future__ import annotations

import importlib
import logging
import pkgutil
from importlib.metadata import entry_points

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "cofy.modules"


def discover_installed_types() -> None:
    """Import every built-in submodule under ``cofy.modules``.

    Each module package's ``__init__.py`` already re-exports its own sources and
    formats, so importing one level of submodules is enough to register everything
    nested underneath it. A submodule whose optional third-party dependency isn't
    installed is skipped rather than aborting discovery of the rest.
    """
    import cofy.modules

    for info in pkgutil.iter_modules(cofy.modules.__path__, prefix="cofy.modules."):
        try:
            importlib.import_module(info.name)
        except ImportError:
            logger.debug("Skipping %s: optional dependency not installed", info.name)


def discover_plugin_types() -> None:
    """Load third-party module/source/format types declared via entry points.

    A downstream package registers by declaring, in its own ``pyproject.toml``::

        [project.entry-points."cofy.modules"]
        my_module = "acme_energy.modules:MyModule"
    """
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        try:
            ep.load()
        except ImportError:
            logger.warning("Failed to load plugin %r (%s): missing dependency", ep.name, ep.value)


def discover_all_types() -> None:
    discover_installed_types()
    discover_plugin_types()
