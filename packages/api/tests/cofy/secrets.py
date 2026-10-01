from collections.abc import Iterator
from contextlib import contextmanager

from cofy.api.references import resolving
from cofy.api.secret import SecretSettings


@contextmanager
def with_secrets(**values: str) -> Iterator[None]:
    """Build settings as a configuration holding these secrets would, for settings built on their own."""
    with resolving(
        [], [SecretSettings.model_validate({"name": name, "value": value}) for name, value in values.items()]
    ):
        yield
