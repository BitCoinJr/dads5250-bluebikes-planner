"""Monthly streamed Bluebikes ingestion with endpoint-specific station matching."""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
from functools import lru_cache
from pathlib import Path
import json
import re
import shutil
import time
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

import pandas as pd
import requests

BUCKET = "https://s3.amazonaws.com/hubway-data/"
STATION_URL = "https://assets.ctfassets.net/p6ae3zqfb1e3/3BswRZgQMp0f8XWBLY6T19/60da57a4630102788a127902bfda9888/-External-_Bluebikes_Station_List__updated_08.21.26_.csv"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@lru_cache(maxsize=8192)
def normalize_name(value):
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(value)).strip()).casefold()


def station_table(path: Path) -> pd.DataFrame:
    """August 2026 CSV has a metadata row before the real header."""
    s = pd.read_csv(path, skiprows=1, dtype=str)
    s = s.rename(columns={"Name": "name", "Municipality": "city", "Total Docks": "docks",
                          "Station ID (to match to historic system data)": "historic_id"})
    s["station_key"] = s.name.map(normalize_name)
    s["docks"] = pd.to_numeric(s.docks, errors="raise").astype(int)
    if s.station_key.duplicated().any() or (s.docks <= 0).any():
        raise ValueError("Ambiguous station names or non-positive capacity")
    return s[["station_key", "name", "city", "docks", "historic_id"]]


def list_objects(prefix: str = "") -> list[dict]:
    ns = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
    objects, token = [], None
    while True:
        params = {"list-type": "2", "prefix": prefix}
        if token:
            params["continuation-token"] = token
        response = requests.get(BUCKET, params=params, timeout=(20, 90))
        response.raise_for_status()
        root = ET.fromstring(response.content)
        for obj in root.findall("s:Contents", ns):
            objects.append({"key": obj.findtext("s:Key", namespaces=ns),
                            "bytes": int(obj.findtext("s:Size", namespaces=ns)),
                            "last_modified": obj.findtext("s:LastModified", namespaces=ns),
                            "etag": obj.findtext("s:ETag", namespaces=ns)})
        token = root.findtext("s:NextContinuationToken", namespaces=ns)
        if not token:
            return objects


def download_ranged(url: str, path: Path, total_bytes: int, workers=4, part_bytes=4 * 1024 * 1024) -> dict:
    """Bounded parallel byte ranges avoid long-stream stalls on the official bucket."""
    parts = path.parent / (path.name + ".ranges")
    parts.mkdir(parents=True, exist_ok=True)
    ranges = [(a, min(a + part_bytes, total_bytes) - 1) for a in range(0, total_bytes, part_bytes)]
    def fetch(bounds):
        begin, end = bounds
        part = parts / str(begin)
        if part.exists() and part.stat().st_size == end - begin + 1:
            return part
        for attempt in range(4):
            try:
                with requests.get(url, headers={"Range": f"bytes={begin}-{end}"}, stream=True, timeout=(20, 45)) as response:
                    response.raise_for_status()
                    if response.status_code != 206 or not response.headers.get("Content-Range", "").startswith(f"bytes {begin}-{end}/"):
                        raise ValueError("Server did not honor requested byte range")
                    with part.open("wb") as handle:
                        for block in response.iter_content(256 * 1024):
                            handle.write(block)
                if part.stat().st_size != end - begin + 1:
                    raise ValueError("Incomplete byte range")
                return part
            except requests.RequestException:
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        completed = list(pool.map(fetch, ranges))
    temp = path.with_suffix(path.suffix + ".part")
    with temp.open("wb") as output:
        for part in completed:
            with part.open("rb") as source:
                shutil.copyfileobj(source, output)
    if temp.stat().st_size != total_bytes:
        raise ValueError("Assembled download size mismatch")
    temp.replace(path)
    return {"url": url, "bytes": total_bytes, "sha256": sha256(path.read_bytes()).hexdigest(),
            "retrieved_utc": utc_now(), "cached": False, "transfer": "parallel verified HTTP byte ranges"}


def download(url: str, path: Path, expected_bytes=None) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if expected_bytes is not None and path.stat().st_size != expected_bytes:
            raise ValueError(f"Cached file size mismatch: {path}; remove this task-local download and retry")
        return {"url": url, "bytes": path.stat().st_size, "sha256": sha256(path.read_bytes()).hexdigest(), "cached": True}
    if expected_bytes is not None and expected_bytes >= 5_000_000:
        return download_ranged(url, path, expected_bytes)
    temp = path.with_suffix(path.suffix + ".part")
    for attempt in range(4):
        offset = temp.stat().st_size if temp.exists() else 0
        try:
            with requests.get(url, stream=True, headers={"Range": f"bytes={offset}-"} if offset else {}, timeout=(20, 45)) as response:
                if response.status_code == 416 and offset and response.headers.get("Content-Range") == f"bytes */{offset}":
                    break
                response.raise_for_status()
                resume = offset > 0 and response.status_code == 206
                with temp.open("ab" if resume else "wb") as handle:
                    for chunk in response.iter_content(256 * 1024):
                        handle.write(chunk)
            break
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    temp.replace(path)
    return {"url": url, "bytes": path.stat().st_size, "sha256": sha256(path.read_bytes()).hexdigest(), "retrieved_utc": utc_now(), "cached": False}


@contextmanager
def trip_readers(path: Path, chunksize=100_000):
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            names = [n for n in archive.namelist() if n.lower().endswith(".csv") and not n.startswith("__MACOSX/")]
            if not names:
                raise ValueError("No CSV files in trip archive")
            yield [(name, lambda n=name: pd.read_csv(archive.open(n), dtype=str, chunksize=chunksize)) for name in names]
    else:
        yield [(path.name, lambda: pd.read_csv(path, dtype=str, chunksize=chunksize))]


def aggregate_trips(path: Path, stations: pd.DataFrame, chunksize=100_000, exclude_ride_ids=None) -> tuple[pd.DataFrame, dict]:
    """Map names (IDs unavailable for newer official stations) without fuzzy guesses.

    Preserve ride IDs as strings; deduplicate non-null ride IDs within an archive.
    Drop invalid duration/timestamps, but map each endpoint independently. Local
    timestamps are wall time America/New_York with no timezone in source; repeated
    fall-back hours are combined and spring-forward absent hours require no fill.
    """
    station_keys = set(stations.station_key)
    exclude_ride_ids = exclude_ride_ids or set()
    parts, seen = [], set()
    stats = Counter()
    unmatched = {"start": Counter(), "end": Counter()}
    columns = []
    min_start = max_start = min_end = max_end = None
    with trip_readers(path, chunksize) as readers:
        members = [name for name, _ in readers]
        for _, reader in readers:
            for chunk in reader():
                if not columns:
                    columns = chunk.columns.tolist()
                required = {"ride_id", "started_at", "ended_at", "start_station_name", "end_station_name"}
                if not required.issubset(chunk.columns):
                    raise ValueError(f"Unsupported schema {chunk.columns.tolist()}")
                stats["raw_rows"] += len(chunk)
                # Null ride IDs retained; exact full-row duplicates inside chunk detected separately.
                stats["exact_duplicate_rows_within_chunks"] += int(chunk.duplicated().sum())
                ids = chunk.ride_id
                stats["missing_ride_id"] += int(ids.isna().sum())
                duplicates = ids.notna() & (ids.isin(seen) | ids.duplicated())
                stats["duplicate_ride_ids_removed"] += int(duplicates.sum())
                seen.update(ids.dropna().tolist())
                chunk = chunk.loc[~duplicates].copy()
                cross_archive = chunk.ride_id.isin(exclude_ride_ids)
                stats["cross_archive_duplicate_ids_removed"] += int(cross_archive.sum())
                chunk = chunk.loc[~cross_archive].copy()
                starts = pd.to_datetime(chunk.started_at, format="mixed", errors="coerce")
                ends = pd.to_datetime(chunk.ended_at, format="mixed", errors="coerce")
                invalid = starts.isna() | ends.isna() | (ends < starts)
                stats["invalid_timestamps_or_negative_duration"] += int(invalid.sum())
                chunk = chunk.loc[~invalid]
                starts, ends = starts.loc[~invalid], ends.loc[~invalid]
                stats["valid_rows"] += len(chunk)
                if len(chunk):
                    min_start = min(starts.min(), min_start) if min_start is not None else starts.min()
                    max_start = max(starts.max(), max_start) if max_start is not None else starts.max()
                    min_end = min(ends.min(), min_end) if min_end is not None else ends.min()
                    max_end = max(ends.max(), max_end) if max_end is not None else ends.max()
                for side, timestamps in [("start", starts), ("end", ends)]:
                    idcol = f"{side}_station_id"
                    if idcol in chunk:
                        stats[f"{side}_missing_station_id"] += int(chunk[idcol].isna().sum())
                    names = chunk[f"{side}_station_name"].map(normalize_name)
                    matched = names.isin(station_keys)
                    stats[f"{side}_matched"] += int(matched.sum())
                    stats[f"{side}_missing_name"] += int((names == "").sum())
                    unmatched[side].update(names.loc[~matched].tolist())
                    frame = pd.DataFrame({"station_key": names.loc[matched], "hour": timestamps.loc[matched].dt.floor("h")})
                    frame["departures"] = int(side == "start")
                    frame["arrivals"] = int(side == "end")
                    frame["ebike_departures"] = (chunk.loc[matched, "rideable_type"].eq("electric_bike").astype(int)
                                                   if side == "start" and "rideable_type" in chunk else 0)
                    parts.append(frame.groupby(["station_key", "hour"], as_index=False)[["departures", "arrivals", "ebike_departures"]].sum())
    if parts:
        hourly = pd.concat(parts, ignore_index=True).groupby(["station_key", "hour"], as_index=False)[["departures", "arrivals", "ebike_departures"]].sum()
    else:
        hourly = pd.DataFrame(columns=["station_key", "hour", "departures", "arrivals", "ebike_departures"])
    result = dict(stats)
    result.update({"columns": columns, "archive_members": members, "hourly_rows": len(hourly),
                   "min_started_at": str(min_start), "max_started_at": str(max_start),
                   "min_ended_at": str(min_end), "max_ended_at": str(max_end),
                   "unmatched_start_names": dict(unmatched["start"].most_common()),
                   "unmatched_end_names": dict(unmatched["end"].most_common()),
                   "dedup_scope": "Non-null ride_id within archive including all chunks and CSV members, plus deterministic cross-archive exclusions supplied by global all-ID audit",
                   "start_join_rate": stats["start_matched"] / max(1, stats["valid_rows"]),
                   "end_join_rate": stats["end_matched"] / max(1, stats["valid_rows"])})
    return hourly, result
