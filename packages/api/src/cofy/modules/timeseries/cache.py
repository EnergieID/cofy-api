import asyncio
import datetime as dt
import logging
import time
from collections import OrderedDict
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass

import narwhals as nw
from pydantic import BaseModel, Field

from .alignment import floor_datetime
from .model import ISODuration, ISOTimedelta, Timeseries

LOGGER = logging.getLogger(__name__)

Segment = tuple[dt.datetime, dt.datetime]
Fetch = Callable[..., Awaitable[Timeseries]]


class CacheSettings(BaseModel):
    """How a source caches what it fetches."""

    max_age: ISOTimedelta | None = Field(
        None, description="How long fetched data stays valid. Defaults to how long the source says its data does."
    )
    chunk_size: ISOTimedelta = Field(
        dt.timedelta(days=1), description="The size of the chunks of time that are fetched and cached as a whole."
    )
    max_chunks: int = Field(1024, description="The most chunks kept in memory, the least recently used evicted first.")


@dataclass
class _Entry:
    frame: nw.DataFrame
    metadata: dict
    fetched_at: float


@dataclass
class _SeriesLock:
    lock: asyncio.Lock
    users: int = 0


class TimeseriesCache:
    def __init__(self, fetch: Fetch, settings: CacheSettings, default_max_age: Callable[[], dt.timedelta | None]):
        """Caches what `fetch` returns in memory, in aligned chunks of time.

        Assumes the fetched series is decomposable: fetching a range returns the same rows as fetching its parts.
        Requests that don't align with the resolution grid, or use a resolution that doesn't divide the chunk
        size, are cached for their exact range instead.

        Args:
            fetch: Fetches the timeseries for a range, as `TimeseriesSource.fetch_timeseries` does.
            settings: How long fetched data stays valid, and in which chunks it is kept.
            default_max_age: How long fetched data stays valid when the settings don't say.
        """
        self._fetch = fetch
        self._settings = settings
        self._default_max_age = default_max_age
        self.chunk_size = settings.chunk_size
        self.max_chunks = settings.max_chunks
        self._entries: OrderedDict[tuple, _Entry] = OrderedDict()
        self._locks: dict[tuple, _SeriesLock] = {}

    @property
    def max_age(self) -> dt.timedelta:
        """How long fetched data stays valid.

        The default is looked up on first use, since what it depends on may only be set once the source is built.
        """
        max_age = self._settings.max_age if self._settings.max_age is not None else self._default_max_age()
        if max_age is None:
            raise ValueError("A cache needs a max_age when its source doesn't declare one")
        return max_age

    async def fetch(
        self,
        start: dt.datetime,
        end: dt.datetime,
        resolution: ISODuration,
        **kwargs,
    ) -> Timeseries:
        start, end = _to_utc(start), _to_utc(end)
        series = (str(resolution), frozenset(kwargs.items()))
        segments = self._segments(start, end, resolution)

        async with self._series_lock(series):
            entries = {segment: entry for segment in segments if (entry := self._fresh_entry(series, segment))}
            runs = _consecutive_runs([segment for segment in segments if segment not in entries])
            fetched = await asyncio.gather(*(self._fetch_run(series, run, resolution, kwargs) for run in runs))
            for run_entries in fetched:
                entries.update(run_entries)

        ordered = [entries[segment] for segment in segments]
        frames = [entry.frame for entry in ordered if len(entry.frame) > 0]
        frame = _slice(nw.concat(frames), start, end) if frames else ordered[0].frame
        latest = max(ordered, key=lambda entry: entry.fetched_at)
        # the result expires with its oldest chunk; stale chunks served after a failed fetch expire right away
        now = time.monotonic()
        remaining = min(self.max_age.total_seconds() - (now - entry.fetched_at) for entry in ordered)
        metadata = dict(latest.metadata)
        metadata["expires"] = dt.datetime.now(dt.UTC) + dt.timedelta(seconds=max(remaining, 0))
        return Timeseries(frame=frame, metadata=metadata)

    @asynccontextmanager
    async def _series_lock(self, series: tuple) -> AsyncGenerator[None]:
        # one lock per series, so a slow fetch only blocks requests for that series,
        # removed once unused so the locks don't grow with every distinct set of extra args
        series_lock = self._locks.setdefault(series, _SeriesLock(asyncio.Lock()))
        series_lock.users += 1
        try:
            async with series_lock.lock:
                yield
        finally:
            series_lock.users -= 1
            if series_lock.users == 0:
                del self._locks[series]

    def _segments(self, start: dt.datetime, end: dt.datetime, resolution: ISODuration) -> list[Segment]:
        chunk_size = self.chunk_size
        chunkable = (
            isinstance(resolution, dt.timedelta)
            and chunk_size % resolution == dt.timedelta(0)
            and floor_datetime(start, resolution) == start
            and floor_datetime(end, resolution) == end
        )
        if not chunkable:
            return [(start, end)]

        segments = []
        chunk_start = floor_datetime(start, chunk_size)
        while chunk_start < end:
            segments.append((chunk_start, chunk_start + chunk_size))
            chunk_start += chunk_size
        return segments

    def _fresh_entry(self, series: tuple, segment: Segment) -> _Entry | None:
        entry = self._entries.get((series, *segment))
        if entry is None or time.monotonic() - entry.fetched_at >= self.max_age.total_seconds():
            return None
        self._entries.move_to_end((series, *segment))
        return entry

    async def _fetch_run(
        self, series: tuple, run: list[Segment], resolution: ISODuration, kwargs: dict
    ) -> dict[Segment, _Entry]:
        run_start, run_end = run[0][0], run[-1][1]
        LOGGER.debug("Fetching [%s, %s)", run_start, run_end)
        try:
            timeseries = await self._fetch(run_start, run_end, resolution, **kwargs)
        except Exception:
            stale = {segment: self._entries.get((series, *segment)) for segment in run}
            if any(entry is None for entry in stale.values()):
                raise
            LOGGER.warning("Fetching [%s, %s) failed, serving stale data", run_start, run_end, exc_info=True)
            return {segment: entry for segment, entry in stale.items() if entry is not None}

        fetched_at = time.monotonic()
        entries = {
            segment: _Entry(_slice(timeseries.frame, *segment), timeseries.metadata, fetched_at) for segment in run
        }
        for segment, entry in entries.items():
            self._store((series, *segment), entry)
        return entries

    def _store(self, key: tuple, entry: _Entry) -> None:
        self._entries[key] = entry
        self._entries.move_to_end(key)
        while len(self._entries) > self.max_chunks:
            self._entries.popitem(last=False)


def _to_utc(value: dt.datetime) -> dt.datetime:
    return value.replace(tzinfo=dt.UTC) if value.tzinfo is None else value.astimezone(dt.UTC)


def _slice(frame: nw.DataFrame, start: dt.datetime, end: dt.datetime) -> nw.DataFrame:
    # an empty frame may lack a proper timestamp column to compare against
    if len(frame) == 0:
        return frame
    return frame.filter((nw.col("timestamp") >= start) & (nw.col("timestamp") < end))


def _consecutive_runs(segments: list[Segment]) -> list[list[Segment]]:
    runs: list[list[Segment]] = []
    for segment in segments:
        if runs and runs[-1][-1][1] == segment[0]:
            runs[-1].append(segment)
        else:
            runs.append([segment])
    return runs
