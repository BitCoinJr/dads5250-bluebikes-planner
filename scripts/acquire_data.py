"""Download official monthly files, verify pilot, then aggregate all requested data.

Run from repo root: py scripts/acquire_data.py --workers 4
Raw archives stay local and are excluded from git. Resuming uses verified caches.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import sys
import time
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd
import numpy as np
from bluebikes.data import BUCKET, STATION_URL, aggregate_trips, download, list_objects, station_table, utc_now
from bluebikes.inventory import inventory_proxy


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--pilot-only", action="store_true")
    args = parser.parse_args()
    metadata, processed, raw = [ROOT / "data" / s for s in ["metadata", "processed", "raw"]]
    for p in [metadata, processed, raw]:
        p.mkdir(parents=True, exist_ok=True)
    station_record = download(STATION_URL, metadata / "stations_original.csv")
    stations = station_table(metadata / "stations_original.csv")
    stations.to_csv(metadata / "stations.csv", index=False)
    station_record.update({"effective_date": "2026-08-21", "download_checked_utc": utc_now(), "rows": len(stations),
                           "cities": stations.city.value_counts().to_dict(),
                           "matching": "Exact NFKC whitespace-normalized casefolded name; official historic numeric IDs incompatible with modern alphanumeric trip IDs"})
    save_json(metadata / "station_source.json", station_record)
    objects = list_objects()
    save_json(metadata / "bucket_manifest.json", {"retrieved_utc": utc_now(), "objects": objects})
    wanted = [f"{y}{m:02d}" for y in [2024, 2025, 2026] for m in range(1, 13 if y < 2026 else 10)]
    # December 2023 provides arrivals on the January 2024 boundary only.
    source_months = ["202312"] + wanted
    chosen, missing = {}, []
    for month in source_months:
        options = [o for o in objects if o["key"].startswith(month + "-bluebikes-tripdata") and o["key"].lower().endswith((".zip", ".csv"))]
        if len(options) != 1:
            missing.append({"month": month, "reason": "missing or ambiguous", "matches": options})
        else:
            chosen[month] = options[0]
    diagnostics = {"started_utc": utc_now(), "requested_months": wanted, "missing": missing,
                   "station_source": station_record, "months": {},
                   "assumptions": ["Daily floor(docks/2) reset included as bike-handling demand", "Net all departures and arrivals within each local hour before inventory correction",
                    "Bike supply and collection each count one handling action; a pickup plus delivery is two actions, not one relocation",
                    "Virtual external depot balances each station's reset and within-day actions; routing, depot stock, travel, timing and truck capacity are unmodelled",
                    "Current station municipality and docks applied retrospectively; unmatched names excluded endpoint by endpoint",
                    "Trips use naive America/New_York wall timestamps; DST repeated hours are netted together", "December 2023 trips used only for January 2024 arrival boundary"]}
    def process(month, force=False):
        cache, detail = processed / f"source_hourly_{month}.parquet", metadata / f"trip_{month}.json"
        if cache.exists() and detail.exists() and not force:
            print(f"cache {month}", flush=True)
            return month, json.loads(detail.read_text(encoding="utf-8"))
        obj = chosen[month]
        path = raw / obj["key"]
        print(f"download {month}: {obj['bytes'] / 1e6:.1f}MB", flush=True)
        record = download(BUCKET + obj["key"], path, expected_bytes=obj["bytes"])
        if path.stat().st_size != obj["bytes"]:
            raise ValueError(f"Size mismatch for {path}")
        exclude_cache = ROOT / "data/cache/ride_ids" / (month + "_exclude.npy")
        exclusions = {f"{int(i):016X}" for i in np.load(exclude_cache)} if exclude_cache.exists() else set()
        hourly, stats = aggregate_trips(path, stations, exclude_ride_ids=exclusions)
        stats.update({"file": obj, "download": record, "source_month": month})
        hourly.to_parquet(cache, index=False)
        save_json(detail, stats)
        print(f"aggregate {month}: {stats['valid_rows']:,} trips; start/end join {stats['start_join_rate']:.1%}/{stats['end_join_rate']:.1%}", flush=True)
        return month, stats
    # Mandatory small pilot before any broad processing.
    month, detail = process("202401")
    diagnostics["months"][month] = detail
    pilot_h = pd.read_parquet(processed / "source_hourly_202401.parquet")
    pilot_stations = stations.loc[stations.city.isin(["Boston", "Cambridge"])]
    pilot_h = pilot_h.loc[pilot_h.station_key.isin(pilot_stations.station_key) & pilot_h.hour.between("2024-01-01", "2024-02-01", inclusive="left")]
    _, pilot = inventory_proxy(pilot_h, pilot_stations)
    pilot.to_csv(processed / "pilot_boston_cambridge_202401.csv", index=False)
    diagnostics["pilot"] = {"month": "202401", "cities": ["Boston", "Cambridge"], "rows": len(pilot_h), "status": "executed_before_full_expansion", "boundary": "Pilot excludes December 2023 arrivals; full run corrects this boundary"}
    save_json(metadata / "diagnostics.json", diagnostics)
    if args.pilot_only:
        print(pilot.to_string(index=False), flush=True)
        return
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(process, m): m for m in source_months if m in chosen and m != "202401"}
        for future in as_completed(futures):
            month, detail = future.result()
            diagnostics["months"][month] = detail
            save_json(metadata / "diagnostics.json", diagnostics)
    # Filename partitioning changes in June 2024. Audit ALL ride IDs globally and
    # correct any affected source cache before inventory aggregation.
    subprocess.run([sys.executable, str(ROOT / "scripts/audit_all_ids.py")], cwd=ROOT, check=True)
    cross_audit = json.loads((metadata / "cross_archive_all_ids.json").read_text(encoding="utf-8"))
    if not cross_audit["all_required_archives_audited"]:
        raise ValueError("Global ID audit incomplete; final monthly output withheld")
    for month, excluded in cross_audit["duplicate_rows_to_exclude_by_source"].items():
        if excluded and diagnostics["months"][month].get("cross_archive_duplicate_ids_removed", 0) != excluded:
            month, detail = process(month, force=True)
            diagnostics["months"][month] = detail
    diagnostics["global_cross_archive_audit"] = {"distinct_ids_in_multiple_archives": cross_audit["global_distinct_ids_in_multiple_archives"],
                                                 "duplicate_rows_removed": sum(cross_audit["duplicate_rows_to_exclude_by_source"].values()),
                                                 "policy": cross_audit["retention"]}
    # Combine all endpoints by their actual event month, including cross-month returns.
    all_monthly, source_ranges = [], {}
    for source in source_months:
        cache = processed / f"source_hourly_{source}.parquet"
        if cache.exists():
            h = pd.read_parquet(cache)
            source_ranges[source] = (h.hour.min(), h.hour.max())
    for month in wanted:
        if month not in diagnostics["months"]:
            continue
        start = pd.Timestamp(month + "01")
        end = start + pd.offsets.MonthBegin(1)
        pieces = []
        for source, (lo, hi) in source_ranges.items():
            if lo < end and hi >= start:
                h = pd.read_parquet(processed / f"source_hourly_{source}.parquet")
                pieces.append(h.loc[(h.hour >= start) & (h.hour < end)])
        hourly = pd.concat(pieces, ignore_index=True).groupby(["station_key", "hour"], as_index=False)[["departures", "arrivals", "ebike_departures"]].sum()
        daily, monthly = inventory_proxy(hourly, stations)
        # Explicit zero cells for municipalities with no matched observed flow, not missing months.
        monthly = stations[["city"]].drop_duplicates().merge(monthly, on="city", how="left")
        monthly["year"], monthly["month"] = start.year, start.month
        numeric = monthly.select_dtypes(include="number").columns
        monthly[numeric] = monthly[numeric].fillna(0)
        all_monthly.append(monthly)
        hourly.to_parquet(processed / f"station_hour_{month}.parquet", index=False)
        daily.to_parquet(processed / f"station_day_{month}.parquet", index=False)
        print(f"proxy {month}: {monthly.demand_bikes.sum():,.0f} handling actions", flush=True)
    result = pd.concat(all_monthly, ignore_index=True).sort_values(["year", "month", "city"])
    result.to_csv(processed / "monthly.csv", index=False)
    diagnostics["completed_utc"] = utc_now()
    diagnostics["output_rows"] = len(result)
    diagnostics["real_valid_trips_in_requested_archives"] = sum(v["valid_rows"] for k,v in diagnostics["months"].items() if k in wanted)
    diagnostics["observed_months"] = sorted(k for k in diagnostics["months"] if k in wanted)
    diagnostics["all_requested_months_observed"] = diagnostics["observed_months"] == wanted
    diagnostics["boundary_convention"] = "All endpoints assigned by actual local date/hour across downloaded archives; Dec2023 supplies Jan2024 arrivals; post-Sep2026 endpoints excluded. Source filename partitioning is inconsistent: Dec2023-May2024 start-month, June2024-March2026 end-month, April2026 start-month, May2026-September2026 end-month. Global ride-ID dedup removes observed overlaps. March2026 starts ending April2026 may be absent from both source files (unquantified internal gap). September2026 starts ending October2026 are unavailable because October archive is not yet published (right-censoring). No missing trips are imputed."
    diagnostics["coverage_limitations"] = {
        "all_requested_files_available_is_not_complete_event_coverage": True,
        "internal_gap": {"transition": "202603_end_month_to_202604_start_month", "affected_event_months": ["202603", "202604"],
                         "description": "Trips starting in March and ending in April may be absent from both official archives", "missing_trip_count": None},
        "right_censoring": {"event_month": "202609", "description": "September departures returning in October are unavailable until October archive publication", "missing_trip_count": None},
        "imputation_performed": False,
        "current_station_metadata_applied_retrospectively": True,
        "unmatched_endpoints_excluded": True}
    save_json(metadata / "diagnostics.json", diagnostics)
    print(f"DONE {len(result)} city-months; {diagnostics['real_valid_trips_in_requested_archives']:,} real valid trips", flush=True)


if __name__ == "__main__":
    main()
