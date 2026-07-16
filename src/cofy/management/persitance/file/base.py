from importlib import resources
from pathlib import Path

import yaml

from cofy.api.cofy_api import CofyAPISettings

from ...errors import ResourceNotFoundError

DEFAULT_BASE_PATH = Path(str(resources.files("cofy.management.persitance.file") / "data"))


class FilePersistence:
    def __init__(self, base_path: Path = DEFAULT_BASE_PATH):
        self.base_path = base_path

    def _community_path(self, slug: str) -> Path:
        return self.base_path / f"{slug}.yaml"

    def _get_community_config(self, slug: str) -> CofyAPISettings:
        path = self._community_path(slug)
        if not path.exists():
            raise ResourceNotFoundError(f"Community {slug!r} not found")

        with path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}

        if not isinstance(loaded, dict):
            raise ValueError(f"Community config at {path} must be a YAML mapping")

        return CofyAPISettings.model_validate(loaded)

    def _save_community_config(self, slug: str, config: CofyAPISettings) -> None:
        path = self._community_path(slug)
        with path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(config.model_dump(exclude_none=True), handle, sort_keys=True)
