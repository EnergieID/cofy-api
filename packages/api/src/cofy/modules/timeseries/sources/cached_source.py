import asyncio
import datetime as dt
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import narwhals as nw

from ..alignment import floor_datetime
from ..model import ISODuration, ISOTimedelta, Timeseries
from ..source import TimeseriesSource, TimeseriesSourceSettings

if TYPE_CHECKING:
    # Published at runtime by finalize(); the base class is the static stand-in.
    AnyTimeseriesSourceSettings = TimeseriesSourceSettings

LOGGER = logging.getLogger(__name__)

Segment = tuple[dt.datetime, dt.datetime]


class CachedTimeseriesSourceSettings(TimeseriesSourceSettings):
    type: Literal["cached"] = "cached"
    source: "AnyTimeseriesSourceSettings"
    max_age: ISOTimedelta | None = None
    chunk_size: ISOTimedelta = dt.timedelta(days=1)
    max_chunks: int = 1024


@dataclass
class _Entry:
    frame: nw.DataFrame
    metadata: dict
    fetched_at: float


class CachedTimeseriesSource(TimeseriesSource, settings=CachedTimeseriesSourceSettings):
    def __init__(
        self,
        source: TimeseriesSource,
        max_age: dt.timedelta | None = None,
        chunk_size: dt.timedelta = dt.timedelta(days=1),
        max_chunks: int = 1024,
    ):
        """A TimeseriesSource that caches the data of the source it wraps in memory, in aligned chunks of time.

        Assumes the wrapped source is decomposable: fetching a range returns the same rows as fetching its parts.
        Requests that don't align with the resolution grid, or use a resolution that doesn't divide the chunk
        size, are cached for their exact range instead.

        Args:
            source: The TimeseriesSource to cache.
            max_age: How long fetched data stays valid. Defaults to the max_age of the wrapped source.
            chunk_size: The size of the chunks of time that are fetched and cached as a whole.
            max_chunks: The maximum number of chunks kept in memory, the least recently used are evicted first.
        """
        max_age = max_age if max_age is not None else source.max_age
        if max_age is None:
            raise ValueError("max_age must be provided when the wrapped source does not declare one")

        self.source = source
        self._max_age = max_age
        self.chunk_size = chunk_size
        self.max_chunks = max_chunks
        self._entries: OrderedDict[tuple, _Entry] = OrderedDict()
        self._locks: dict[tuple, asyncio.Lock] = {}

    async def fetch_timeseries(
        self,
        start: dt.datetime,
        end: dt.datetime,
        resolution: ISODuration,
        **kwargs,
    ) -> Timeseries:
        start, end = _to_utc(start), _to_utc(end)
        series = (str(resolution), frozenset(kwargs.items()))
        segments = self._segments(start, end, resolution)

        async with self._locks.setdefault(series, asyncio.Lock()):
            entries = {segment: entry for segment in segments if (entry := self._fresh_entry(series, segment))}
            runs = _consecutive_runs([segment for segment in segments if segment not in entries])
            fetched = await asyncio.gather(*(self._fetch_run(series, run, resolution, kwargs) for run in runs))
            for run_entries in fetched:
                entries.update(run_entries)

        ordered = [entries[segment] for segment in segments]
        frames = [entry.frame for entry in ordered if len(entry.frame) > 0]
        frame = _slice(nw.concat(frames), start, end) if frames else ordered[0].frame
        latest = max(ordered, key=lambda entry: entry.fetched_at)
        return Timeseries(frame=frame, metadata=dict(latest.metadata))

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
        if entry is None or time.monotonic() - entry.fetched_at >= self._max_age.total_seconds():
            return None
        self._entries.move_to_end((series, *segment))
        return entry

    async def _fetch_run(
        self, series: tuple, run: list[Segment], resolution: ISODuration, kwargs: dict
    ) -> dict[Segment, _Entry]:
        run_start, run_end = run[0][0], run[-1][1]
        LOGGER.debug("Fetching [%s, %s) from %s", run_start, run_end, type(self.source).__name__)
        try:
            timeseries = await self.source.fetch_timeseries(run_start, run_end, resolution, **kwargs)
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

    @property
    def supported_resolutions(self) -> list[str]:
        return self.source.supported_resolutions

    @property
    def extra_args(self) -> dict:
        return self.source.extra_args

    @property
    def max_age(self) -> dt.timedelta:
        return self._max_age


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
