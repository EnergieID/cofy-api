from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

from .api import CofyAPI, Module, ModuleSettings
from .version import __version__

__all__ = [
    "CofyAPI",
    "Module",
    "ModuleSettings",
    "__version__",
]
