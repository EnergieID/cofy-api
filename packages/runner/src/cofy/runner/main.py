import datetime as dt
import logging
import os
from pathlib import Path

import isodate
from cofy.modules.discovery import discover_all_types

from .runner import CommunityRunner

DIRECTORY_ENV_VAR = "COFY_RUNNER_DIRECTORY"
COMMUNITIES_ENV_VAR = "COFY_RUNNER_COMMUNITIES"
POLL_INTERVAL_ENV_VAR = "COFY_RUNNER_POLL_INTERVAL"


def directory_from_env() -> Path:
    """The directory of community settings to serve."""
    configured = os.environ.get(DIRECTORY_ENV_VAR)
    if not configured:
        raise RuntimeError(f"{DIRECTORY_ENV_VAR} must be set to the directory of community settings to serve")
    return Path(configured)


def communities_from_env() -> frozenset[str] | None:
    """The slugs to serve, comma separated, or every community when unset."""
    configured = os.environ.get(COMMUNITIES_ENV_VAR)
    if not configured:
        return None
    return frozenset(slug.strip() for slug in configured.split(",") if slug.strip())


def poll_interval_from_env() -> dt.timedelta:
    """How often to check for changed settings, as an ISO 8601 duration; `PT2S` by default."""
    configured = os.environ.get(POLL_INTERVAL_ENV_VAR, "PT2S")
    try:
        interval = isodate.parse_duration(configured)
    except isodate.ISO8601Error as exc:
        raise RuntimeError(f"{POLL_INTERVAL_ENV_VAR} must be an ISO 8601 duration, such as PT2S") from exc
    if not isinstance(interval, dt.timedelta) or interval <= dt.timedelta(0):
        raise RuntimeError(f"{POLL_INTERVAL_ENV_VAR} must be a positive duration without months or years")
    return interval


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# Register every installed module, source and format type, so the settings can use any of them.
discover_all_types()

app = CommunityRunner(directory_from_env(), communities_from_env(), poll_interval_from_env())
