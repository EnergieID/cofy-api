from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, Any

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, create_engine

from src.cofy.db.database_backed_source import DatabaseBackedSource

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

    from src.shared.module import Module


class CofyDB:
    def __init__(self, url: str | None = None, **engine_kwargs):
        if url is None:
            raise ValueError("CofyDB requires a database URL to be configured.")
        self._sources: list[DatabaseBackedSource] = []
        self._url = url
        self.engine: Engine = create_engine(self._url, **engine_kwargs)

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

    def _build_config(self) -> Config:
        config = Config()
        config.set_main_option(
            "script_location", str(resources.files("src.cofy.db").joinpath("alembic"))
        )
        config.set_main_option("sqlalchemy.url", self._url)
        config.set_main_option("path_separator", "os")

        if self.migration_locations:
            config.set_main_option(
                "version_locations", " ".join(self.migration_locations)
            )

        config.attributes["target_metadata"] = self.target_metadata
        return config

    def run_migrations(self, revision: str = "heads") -> None:
        command.upgrade(self._build_config(), revision)

    def generate_migration(
        self,
        message: str,
        head: str,
        rev_id: str | None = None,
        autogenerate: bool = True,
    ) -> None:
        """Generate a new Alembic migration revision for a specific module branch.

        Args:
            message: Description of the migration.
            head: The branch head to extend, e.g. "members_core@head".
            rev_id: Optional custom revision ID. If None, Alembic generates one.
            autogenerate: Whether to autogenerate the migration from model changes.
        """
        command.revision(
            self._build_config(),
            message=message,
            autogenerate=autogenerate,
            head=head,
            rev_id=rev_id,
        )

    def reset(self) -> None:
        """usefull in development to reset the database to a clean state
        Warning: this will delete all data in the database, use with caution!
        """
        meta = MetaData()
        meta.reflect(bind=self.engine)
        meta.drop_all(bind=self.engine)
        self.run_migrations()
