"""Offline station-coordinate context for existing monthly staffing plans.

Station means are plotting anchors, not crew depots. Shared-pool crews are
reported separately and are never assigned a geographic bubble or duplicated.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from html import escape
import calendar
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .planner import CORE_CITIES, OTHER_POOL

AREA_PER_CREW = 90.0  # points squared; constant for every panel and every month.
LEGEND_CREWS = (1, 5, 10)
OFFSETS = {"Boston": (24, -37), "Cambridge": (-66, 16),
           "Somerville": (34, 53), "Brookline": (-78, -35)}


def _safe(value):
    return escape(str(value), quote=True)


@lru_cache(maxsize=4)
def _load_cached(path_text, modified_ns, byte_count):
    path = Path(path_text)
    raw = pd.read_csv(path, skiprows=1, dtype=str)
    required = {"Name", "Lat", "Long", "Municipality", "Total Docks"}
    if not required.issubset(raw.columns):
        raise ValueError("Station snapshot columns do not match the official format")
    data = raw.rename(columns={"Name": "name", "Lat": "latitude", "Long": "longitude",
                               "Municipality": "city", "Total Docks": "docks"})
    if data[["name", "city"]].isna().any().any() or data.name.str.strip().eq("").any() or data.city.str.strip().eq("").any():
        raise ValueError("Station names and municipalities must be present")
    if data.name.str.normalize("NFKC").str.strip().str.casefold().duplicated().any():
        raise ValueError("Station names are not unique")
    data["docks"] = pd.to_numeric(data.docks, errors="raise")
    if (data.docks <= 0).any() or (data.docks % 1 != 0).any():
        raise ValueError("Dock counts must be positive whole numbers")
    data["latitude"] = pd.to_numeric(data.latitude, errors="coerce")
    data["longitude"] = pd.to_numeric(data.longitude, errors="coerce")
    data["valid_coordinates"] = (data.latitude.between(-90, 90) & data.longitude.between(-180, 180)
                                  & np.isfinite(data.latitude) & np.isfinite(data.longitude))
    columns = ["name", "city", "latitude", "longitude", "docks", "valid_coordinates"]
    # Immutable cached records; the public helper creates a defensive DataFrame.
    return tuple(tuple(row) for row in data[columns].itertuples(index=False, name=None))


def load_stations(root=None):
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    path = root / "data/metadata/stations_original.csv"
    info = path.stat()
    rows = _load_cached(str(path.resolve()), info.st_mtime_ns, info.st_size)
    data = pd.DataFrame(rows, columns=["name", "city", "latitude", "longitude", "docks", "valid_coordinates"])
    data.attrs.update(source_rows=len(data), valid_coordinate_rows=int(data.valid_coordinates.sum()),
                      source="Current official station snapshot; Municipality and coordinates")
    return data


def _blank():
    return {"figure": None, "pool_md": "", "note_md": ""}


def _valid_stations(stations):
    if not isinstance(stations, pd.DataFrame) or not {"city", "latitude", "longitude"}.issubset(stations.columns):
        return pd.DataFrame()
    data = stations.copy(deep=True)
    data["latitude"] = pd.to_numeric(data.latitude, errors="coerce")
    data["longitude"] = pd.to_numeric(data.longitude, errors="coerce")
    valid = (data.latitude.between(-90, 90) & data.longitude.between(-180, 180)
             & np.isfinite(data.latitude) & np.isfinite(data.longitude)
             & data.city.map(lambda city: isinstance(city, str) and bool(city.strip())))
    return data.loc[valid].copy()


def _plan_frame(records):
    try:
        frame = pd.DataFrame(records)
    except (TypeError, ValueError):
        return None
    required = ["year", "month", "city", "full_time", "seasonal", "demand_bikes"]
    if frame.empty or not set(required).issubset(frame.columns):
        return None
    frame = frame.copy(deep=True)
    numeric = ["year", "month", "full_time", "seasonal", "demand_bikes"]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(frame[numeric].to_numpy(dtype=float)).all():
        return None
    if (frame[["full_time", "seasonal", "demand_bikes"]] < 0).any().any():
        return None
    if (frame[["year", "month", "full_time", "seasonal"]] % 1 != 0).any().any() or not frame.month.between(1, 12).all():
        return None
    if frame.duplicated(["year", "month", "city"]).any() or not set(frame.city).issubset(set(CORE_CITIES) | {OTHER_POOL}):
        return None
    return frame


def geographic_result_from_chain(chain, conversion=1):
    """Reshape saved group-month before/after columns; never solve or rescale."""
    if (not isinstance(chain, pd.DataFrame) or isinstance(conversion, bool)
            or conversion not in (1, 2)):
        return {}
    keys = ["year", "month", "city"]
    measures = ["full_time", "seasonal", "demand_bikes", "capacity_bikes", "unmet_bikes"]
    required = keys + [name + "_" + suffix for suffix in ["base", "scenario"] for name in measures]
    if chain.empty or not set(required).issubset(chain.columns):
        return {}
    plans = {}
    for suffix in ["base", "scenario"]:
        selected = chain[keys + [name + "_" + suffix for name in measures]].copy(deep=True)
        selected = selected.rename(columns={name + "_" + suffix: name for name in measures})
        plans[suffix] = selected.astype(object).where(pd.notna(selected), None).to_dict("records")
    return {"summary": {"handling_actions_per_course_bike": conversion}, "geographic_plans": plans}


def render_geography(result, month, stations):
    """Render cached plan coordinates only; no network, data writes or planning."""
    if (not isinstance(result, dict) or isinstance(month, bool)
            or not isinstance(month, (int, float, np.integer, np.floating))
            or not np.isfinite(month) or int(month) != month or not 1 <= month <= 12):
        return _blank()
    data = deepcopy(result)
    plans = data.get("geographic_plans")
    summary = data.get("summary") or {}
    if not isinstance(plans, dict) or not isinstance(summary, dict):
        return _blank()
    conversion = summary.get("handling_actions_per_course_bike")
    if isinstance(conversion, bool) or conversion not in (1, 2):
        return _blank()
    base, scenario = _plan_frame(plans.get("base")), _plan_frame(plans.get("scenario"))
    if base is None or scenario is None:
        return _blank()
    base = base[base.month == month].copy()
    scenario = scenario[scenario.month == month].copy()
    if (base.empty or scenario.empty or len(set(base.year) | set(scenario.year)) != 1
            or set(base.city) != set(scenario.city)):
        return _blank()
    valid = _valid_stations(stations)
    if valid.empty:
        return _blank()
    centers = valid.groupby("city")[["latitude", "longitude"]].mean()
    base, scenario = base.set_index("city"), scenario.set_index("city")
    year = int(base.year.iloc[0])
    caption = calendar.month_name[int(month)] + " " + str(year)
    lat_min, lat_max = float(valid.latitude.min()), float(valid.latitude.max())
    lon_min, lon_max = float(valid.longitude.min()), float(valid.longitude.max())
    lat_pad = max((lat_max-lat_min) * .12, .005)
    lon_pad = max((lon_max-lon_min) * .12, .005)
    xlim, ylim = (lon_min-lon_pad, lon_max+lon_pad), (lat_min-lat_pad, lat_max+lat_pad)
    aspect = 1 / math.cos(math.radians(float(valid.latitude.mean())))
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.5), sharex=True, sharey=True, layout="constrained")
    missing = [city for city in CORE_CITIES if city in base.index and city not in centers.index]
    for ax, plan, title, color in zip(axes, [base, scenario],
        ["Baseline: no event increment", "Reviewed event scenario"], ["#4478a8", "#238978"]):
        ax.scatter(valid.longitude, valid.latitude, s=5, color="#9ba6af", alpha=.5,
                   label="Station locations only", zorder=1)
        for index, city in enumerate(sorted(set(centers.index) - set(CORE_CITIES))):
            anchor = centers.loc[city]
            ax.annotate(_safe(city), (anchor.longitude, anchor.latitude),
                        xytext=(3, 4 + (index % 2) * 2), textcoords="offset points",
                        fontsize=7, color="#505b66", zorder=4)
        for city in CORE_CITIES:
            if city not in centers.index or city not in plan.index:
                continue
            anchor, row = centers.loc[city], plan.loc[city]
            total = int(row.full_time + row.seasonal)
            prior_total = int(base.loc[city, "full_time"] + base.loc[city, "seasonal"])
            ax.scatter([anchor.longitude], [anchor.latitude], s=[total * AREA_PER_CREW],
                       color=color, alpha=.58, edgecolors="white", linewidths=.9,
                       label="_core_crews_" + city, zorder=3)
            text = (_safe(city) + "\nFT " + str(int(row.full_time)) + " | S " + str(int(row.seasonal))
                    + " | Total " + str(total) + "\n\u0394 total " + format(total-prior_total, "+d")
                    + "\nProxy " + format(float(row.demand_bikes)*conversion, ",.0f") + " actions")
            ax.annotate(text, (anchor.longitude, anchor.latitude), xytext=OFFSETS[city],
                        textcoords="offset points", fontsize=8, color="#223343",
                        arrowprops={"arrowstyle": "-", "color": "#6c7d89", "lw": .7},
                        bbox={"facecolor": "white", "edgecolor": "none", "alpha": .86, "pad": 2}, zorder=5)
        ax.set(xlim=xlim, ylim=ylim, xlabel="Longitude", title=title)
        ax.set_aspect(aspect, adjustable="box")
        ax.ticklabel_format(useOffset=False, style="plain")
        ax.tick_params(labelsize=8)
        ax.grid(alpha=.15)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Latitude")
    size_handles = [axes[1].scatter([], [], s=n*AREA_PER_CREW, color="#7c929f", alpha=.58,
                    edgecolors="white", label=str(n) + (" crew" if n == 1 else " crews")) for n in LEGEND_CREWS]
    axes[1].legend(handles=size_handles, title="Bubble area = total crews", fontsize=8,
                   title_fontsize=8, loc="upper left", framealpha=.9, labelspacing=1.0,
                   handleheight=4.2, handlelength=3.8, borderpad=1.2)
    fig.suptitle(caption + " - core-city staffing with station context", x=.02, ha="left", fontsize=13)
    plt.close(fig)
    pool_lines = ["**Other cities shared pool - no geographic crew assignment**",
                  "This is one integer crew pool for the remaining municipalities, not one allocation per city."]
    if OTHER_POOL in base.index:
        before, after = base.loc[OTHER_POOL], scenario.loc[OTHER_POOL]
        total_before, total_after = int(before.full_time+before.seasonal), int(after.full_time+after.seasonal)
        pool_lines.append(f"**{caption}:** FT {int(before.full_time)} -> {int(after.full_time)}; "
                          f"seasonal {int(before.seasonal)} -> {int(after.seasonal)}; "
                          f"total {total_before} -> {total_after} (change {total_after-total_before:+d}).")
        pool_lines.append("Forecast-demand proxy: "
                          + format(float(before.demand_bikes)*conversion, ",.0f") + " -> "
                          + format(float(after.demand_bikes)*conversion, ",.0f") + " handling actions.")
    else:
        pool_lines.append("No shared-pool plan row is available for this month; no count is fabricated.")
    notes = [
        "**Offline coordinate plot, without basemap tiles.** Small dots are station locations only. "
        "Core-city representative points are unweighted means of valid station coordinates, "
        "**not crew bases, depots or event locations**. Bubble area is proportional to FT + seasonal crews "
        "with the same scale in both panels and all twelve months; change is relative to the baseline.",
        "The axes keep the extent of all valid stations, with the same local geographic scale in both panels. "
        "There are no station-demand estimates, event coordinates, route estimates or station-hour service guarantees.",
        "The course stays at 120 bikes/shift. Demand below comes from the existing city-group forecast, "
        "converted with " + str(conversion) + " handling action(s) per course-bike unit; it is not observed station demand.",
    ]
    demands = []
    for city in CORE_CITIES:
        if city in base.index:
            demands.append(_safe(city) + " " + format(float(base.loc[city, "demand_bikes"])*conversion, ",.0f")
                           + " -> " + format(float(scenario.loc[city, "demand_bikes"])*conversion, ",.0f"))
    if demands:
        notes.append("**Core-group forecast proxy (handling actions):** " + "; ".join(demands) + ".")
    if missing:
        notes.append("**No valid coordinates; omitted, not relocated:** " + ", ".join(_safe(city) for city in missing) + ".")
    omitted = len(stations) - len(valid)
    if omitted:
        notes.append(str(omitted) + " station row(s) with missing/invalid coordinates are excluded from plotting and means.")
    return {"figure": fig, "pool_md": "\n\n".join(pool_lines), "note_md": "\n\n".join(notes)}
