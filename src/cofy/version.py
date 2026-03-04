from importlib.metadata import PackageNotFoundError, version


def get_installed_version() -> str:
    try:
        return version("cofy-api")
    except PackageNotFoundError:
        return "0.0.0"


__version__ = get_installed_version()

__all__ = ["__version__", "get_installed_version"]
