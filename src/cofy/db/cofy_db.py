from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, Any

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from src.cofy.db.database_backed_source import DatabaseBackedSource

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

    from src.shared.module import Module


class CofyDB:
    def __init__(
        self,
        db_url: str | None = None,
        engine_kwargs: dict[str, Any] | None = None,
    ):
        self._sources: list[DatabaseBackedSource] = []
        self._db_url = db_url
        self._engine_kwargs = engine_kwargs or {}
        self._engine: Engine | None = None

    def register_module(self, module: Module):
        source = getattr(module, "source", None)
        if isinstance(source, DatabaseBackedSource):
            self._sources.append(source)

    @property
    def migration_locations(self) -> list[str]:
        locations: list[str] = []
        for source in self._sources:
            for location in source.migration_locations:
                resolved_location = str(Path(location).resolve())
                if resolved_location not in locations:
                    locations.append(resolved_location)
        return locations

    @property
    def target_metadata(self) -> list[Any]:
        metadata: list[Any] = []
        for source in self._sources:
            if (
                source.target_metadata is not None
                and source.target_metadata not in metadata
            ):
                metadata.append(source.target_metadata)
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
