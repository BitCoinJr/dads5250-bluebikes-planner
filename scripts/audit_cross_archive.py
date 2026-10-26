"""Audit cross-archive ride IDs among actual calendar-boundary trip rows.

Only the small set of boundary records is retained in ignored data/cache/audit.
The committed metadata contains counts and hashed IDs, never raw trip records.
This is a boundary-scope audit, not an all-row global deduplication proof.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import time
import zipfile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ["ride_id", "started_at", "ended_at"]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def read_chunks(path, fields=FIELDS):
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            members = sorted(n for n in archive.namelist() if n.lower().endswith(".csv") and not n.startswith("__MACOSX/"))
            if not members:
                raise ValueError(f"No trip CSV in {path.name}")
            for member in members:
                with archive.open(member) as handle:
                    yield from pd.read_csv(handle, usecols=lambda c: c in fields, dtype=str, chunksize=100000)
    else:
        yield from pd.read_csv(path, usecols=lambda c: c in fields, dtype=str, chunksize=100000)


def inspect_file(path, source_month, cache, expected):
    signature = {"bytes": path.stat().st_size, "mtime_ns": path.stat().st_mtime_ns,
                 "expected_etag": expected.get("etag")}
    info_path = cache / f"{source_month}_summary.json"
    rows_path = cache / f"{source_month}_boundary.csv"
    if info_path.exists() and rows_path.exists():
        prior = json.loads(info_path.read_text())
        if prior.get("local_file_signature") == signature:
            return prior, pd.read_csv(rows_path, dtype=str)
    stats = Counter()
    pieces = []
    period = int(source_month)
    for chunk in read_chunks(path):
        if not set(FIELDS).issubset(chunk.columns):
            raise ValueError(f"Missing audit columns in {path.name}")
        stats["raw_rows"] += len(chunk)
        starts = pd.to_datetime(chunk.started_at, errors="coerce", format="mixed")
        ends = pd.to_datetime(chunk.ended_at, errors="coerce", format="mixed")
        stats["missing_or_invalid_start_timestamp"] += int(starts.isna().sum())
        stats["missing_or_invalid_end_timestamp"] += int(ends.isna().sum())
        stats["missing_ride_id"] += int(chunk.ride_id.isna().sum())
        start_out = starts.notna() & (starts.dt.year * 100 + starts.dt.month).ne(period)
        end_out = ends.notna() & (ends.dt.year * 100 + ends.dt.month).ne(period)
        stats["start_outside_source_month"] += int(start_out.sum())
        stats["end_outside_source_month"] += int(end_out.sum())
        stats["both_endpoints_outside_source_month"] += int((start_out & end_out).sum())
        boundary = start_out | end_out
        stats["boundary_rows"] += int(boundary.sum())
        if boundary.any():
            part = chunk.loc[boundary, FIELDS].copy()
            part["source_month"] = source_month
            pieces.append(part)
    rows = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame(columns=FIELDS + ["source_month"])
    if not stats["start_outside_source_month"] and stats["end_outside_source_month"]:
        partition = "start-month partition consistent"
    elif not stats["end_outside_source_month"] and stats["start_outside_source_month"]:
        partition = "end-month partition consistent"
    elif not stats["start_outside_source_month"] and not stats["end_outside_source_month"]:
        partition = "undetermined: all observed endpoints inside source month"
    else:
        partition = "mixed or long-trip endpoints; review required"
    summary = {"source_month": source_month, "file": path.name, **dict(stats),
               "local_file_signature": signature, "partition_diagnostic": partition,
               "boundary_duplicate_ids_within_archive": int(rows.ride_id.dropna().duplicated().sum())}
    rows.to_csv(rows_path, index=False)
    info_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary, rows


def _duplicate_details(paths, duplicate_ids, cache):
    """Local-only full context for correction; no raw trip records in metadata."""
    parts = []
    wanted = set(duplicate_ids)
    fields = FIELDS + ["start_station_name", "end_station_name", "start_station_id", "end_station_id"]
    for month, path in paths.items():
        for chunk in read_chunks(path, fields):
            part = chunk.loc[chunk.ride_id.isin(wanted)].copy()
            if len(part):
                part["source_month"] = month
                part["source_file"] = path.name
                parts.append(part)
    details = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=fields + ["source_month", "source_file"])
    details.to_csv(cache / "cross_archive_duplicate_rows_PRIVATE_LOCAL.csv", index=False)
    return details


def audit(months=None):
    raw = ROOT / "data/raw"
    cache = ROOT / "data/cache/audit"
    cache.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "data/metadata/bucket_manifest.json").read_text())
    expected_months = ["202312"] + [f"{y}{m:02d}" for y in (2024, 2025, 2026) for m in range(1, 13 if y < 2026 else 10)]
    requested = months or expected_months
    objects = {o["key"]: o for o in manifest["objects"]}
    paths, summaries, boundary_parts, missing = {}, [], [], []
    for month in requested:
        candidates = [p for p in raw.glob(month + "-bluebikes-tripdata*") if p.is_file() and p.suffix.lower() in (".zip", ".csv")]
        complete = [p for p in candidates if p.name in objects and p.stat().st_size == objects[p.name]["bytes"]]
        if len(complete) != 1:
            missing.append({"month": month, "reason": "no unique complete raw file", "candidate_files": [p.name for p in candidates]})
            continue
        path = complete[0]
        paths[month] = path
        print(f"audit {month}: {path.name}", flush=True)
        summary, boundary = inspect_file(path, month, cache, objects[path.name])
        summaries.append(summary)
        boundary_parts.append(boundary)
    boundary = pd.concat(boundary_parts, ignore_index=True) if boundary_parts else pd.DataFrame(columns=FIELDS + ["source_month"])
    valid = boundary.dropna(subset=["ride_id"])
    month_counts = valid.groupby("ride_id").source_month.nunique()
    duplicate_ids = month_counts[month_counts > 1].index.tolist()
    duplicated = valid[valid.ride_id.isin(duplicate_ids)]
    pairs = Counter()
    duplicate_records = []
    for ride_id, group in duplicated.groupby("ride_id"):
        files = sorted(group.source_month.unique())
        for first, a in enumerate(files):
            for b in files[first + 1:]:
                pairs[(a, b)] += 1
        duplicate_records.append({"ride_id_sha256": sha256(ride_id.encode()).hexdigest(),
                                  "source_months": files, "boundary_occurrences": len(group)})
    if duplicate_ids:
        involved = set(duplicated.source_month)
        details = _duplicate_details({m: p for m, p in paths.items() if m in involved}, duplicate_ids, cache)
        detail_rows = len(details)
    else:
        detail_rows = 0
    transitions = []
    by_month = {s["source_month"]: s for s in summaries}
    for prior, current in zip(expected_months, expected_months[1:]):
        if prior not in by_month or current not in by_month:
            continue
        previous_rule = by_month[prior]["partition_diagnostic"]
        current_rule = by_month[current]["partition_diagnostic"]
        if previous_rule.startswith("start-month") and current_rule.startswith("end-month"):
            transitions.append({"earlier_source_month": prior, "later_source_month": current,
                                "change": "start-month to end-month",
                                "risk": "Cross-boundary trips can occur in both archives; observed duplicate IDs require correction."})
        elif previous_rule.startswith("end-month") and current_rule.startswith("start-month"):
            transitions.append({"earlier_source_month": prior, "later_source_month": current,
                                "change": "end-month to start-month",
                                "risk": "Cross-boundary trips starting in the earlier month and ending in the later month may be absent from both official files. Their number cannot be established from these archives; no imputation is justified."})
    result = {
        "audit_executed_utc": utc_now(),
        "scope": "Only rows with a valid started_at or ended_at month outside the filename month are retained and compared. Detection requires boundary rows in at least two archives. This is not an all-row cross-archive uniqueness proof: an in-month original duplicated into a wrong-month file can be missed because only the wrong-month copy is retained. The scope detects overlap caused by an otherwise honest change between start-month and end-month partition conventions.",
        "source_partition_warning": "Observed monthly archive partition varies, including switches during 2024 and 2026. Complete acquisition of all files does not establish complete trip coverage: partition switches may create overlaps or unquantified gaps. Assign endpoints to actual timestamps, correct observed repeated IDs, disclose gaps and September 2026 right-censoring, and do not impute missing trips.",
        "partition_transitions": transitions,
        "requested_months": requested,
        "audited_months": sorted(paths),
        "missing_raw_files": missing,
        "all_34_expected_raw_archives_audited": sorted(paths) == expected_months,
        "raw_rows_scanned": sum(s["raw_rows"] for s in summaries),
        "boundary_rows_examined": len(boundary),
        "distinct_boundary_ride_ids": int(valid.ride_id.nunique()),
        "cross_archive_duplicate_ride_ids": len(duplicate_ids),
        "cross_archive_duplicate_boundary_rows": len(duplicated),
        "duplicate_file_pairs": [{"source_month_a": a, "source_month_b": b, "duplicate_ride_ids": count} for (a, b), count in sorted(pairs.items())],
        "hashed_duplicate_id_examples": duplicate_records[:20],
        "private_local_correction_detail_rows": detail_rows,
        "files": summaries,
    }
    (ROOT / "data/metadata/cross_archive_audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ["all_34_expected_raw_archives_audited", "raw_rows_scanned", "boundary_rows_examined", "cross_archive_duplicate_ride_ids", "duplicate_file_pairs"]}, indent=2), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--months", nargs="+", help="Optional partial audit such as 202405 202406")
    parser.add_argument("--wait-for-all", action="store_true", help="Audit new complete files every 30 seconds until all 34 exist")
    args = parser.parse_args()
    while True:
        result = audit(args.months)
        if not args.wait_for_all or result["all_34_expected_raw_archives_audited"]:
            break
        print("Waiting for remaining complete raw files; summaries/boundary records cached locally.", flush=True)
        time.sleep(30)


if __name__ == "__main__":
    main()
