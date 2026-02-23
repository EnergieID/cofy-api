from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DatabaseBackedSource(Protocol):
    @property
    def migration_locations(self) -> Sequence[str]:
        """Filesystem paths containing alembic version files."""

    @property
    def target_metadata(self) -> Any | None:
        """SQLAlchemy metadata used for migration autogeneration."""
