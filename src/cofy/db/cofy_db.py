from __future__ import annotations

from importlib import resources
from typing import TYPE_CHECKING, Any

from alembic import command
from alembic.config import Config
from sqlmodel import create_engine

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

    from src.shared.module import Module


class CofyDB:
    def __init__(
        self,
        db_url: str | None = None,
        engine_kwargs: dict[str, Any] | None = None,
    ):
        self._modules: list[Module] = []
        self._db_url = db_url
        self._engine_kwargs = engine_kwargs or {}
        self._engine: Engine | None = None

    def register_module(self, module: Module):
        if module.uses_database:
            self._modules.append(module)

    @property
    def migration_locations(self) -> list[str]:
        locations: list[str] = []
        for module in self._modules:
            for location in module.resolved_migration_locations:
                if location not in locations:
                    locations.append(location)
        return locations

    @property
    def target_metadata(self) -> list[Any]:
        metadata: list[Any] = []
        for module in self._modules:
            if module.target_metadata not in metadata:
                metadata.append(module.target_metadata)
        return metadata

    @property
    def engine(self):
        if self._engine is None:
            if self._db_url is None:
                raise ValueError("No database URL configured for CofyDB.")
            self._engine = create_engine(self._db_url, **self._engine_kwargs)
        return self._engine

    def run_migrations(self, revision: str = "heads") -> None:
        if self._db_url is None:
            raise ValueError("No database URL configured for CofyDB.")

        config = Config()
        config.set_main_option(
            "script_location", str(resources.files("src.cofy.db").joinpath("alembic"))
        )
        config.set_main_option("sqlalchemy.url", self._db_url)

        if self.migration_locations:
            config.set_main_option(
                "version_locations", " ".join(self.migration_locations)
            )

        config.attributes["target_metadata"] = self.target_metadata
        command.upgrade(config, revision)
