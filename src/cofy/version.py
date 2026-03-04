from importlib.metadata import version


def get_installed_version() -> str:
    v = version("cofy-api")
    if v.startswith("0.0.0"):
        v = "Dev"
    return v


__version__ = get_installed_version()

__all__ = ["__version__", "get_installed_version"]
