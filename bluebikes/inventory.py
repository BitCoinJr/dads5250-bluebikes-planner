"""Transparent station-hour inventory proxy; quantities are bike-handling actions."""
from __future__ import annotations

import numpy as np
import pandas as pd


def inventory_proxy(hourly: pd.DataFrame, stations: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reset each station to floor(docks/2) daily; net arrivals/departures per hour.

    Virtual depot supplies shortages / collects overflow to keep inventory feasible.
    Count each supplied OR collected bike as one handling action (not a completed
    origin-destination relocation). Daily reset handling is included separately.
    Hours with no trips do not change inventory; inactive whole days add zero.
    """
    columns = ["station_key", "hour", "departures", "arrivals", "ebike_departures"]
    h = hourly[columns].copy()
    if h.empty:
        return pd.DataFrame(), pd.DataFrame()
    h["hour"] = pd.to_datetime(h["hour"])
    h = h.merge(stations[["station_key", "city", "docks"]], on="station_key", validate="many_to_one")
    h["day"] = h.hour.dt.normalize()
    h = h.sort_values(["station_key", "day", "hour"])
    records = []
    keys, days = h.station_key.to_numpy(), h.day.to_numpy()
    docks, cities = h.docks.to_numpy(), h.city.to_numpy()
    deps, arrs, ebikes = [h[c].to_numpy(dtype=np.int64) for c in ["departures", "arrivals", "ebike_departures"]]
    boundaries = np.r_[0, np.flatnonzero((keys[1:] != keys[:-1]) | (days[1:] != days[:-1])) + 1, len(h)]
    # Iterate short numeric arrays instead of constructing a DataFrame per station-day.
    for begin, end in zip(boundaries[:-1], boundaries[1:]):
        capacity = int(docks[begin])
        initial = capacity // 2
        inventory = initial
        supply = collection = 0
        for departures_hour, arrivals_hour in zip(deps[begin:end], arrs[begin:end]):
            unconstrained = inventory + int(arrivals_hour) - int(departures_hour)
            supply += max(-unconstrained, 0)
            collection += max(unconstrained - capacity, 0)
            inventory = min(capacity, max(0, unconstrained))
        reset_supply = max(initial - inventory, 0)
        reset_collection = max(inventory - initial, 0)
        departures = int(deps[begin:end].sum())
        arrivals = int(arrs[begin:end].sum())
        # Daily conservation includes the virtual depot and the next day's reset.
        assert arrivals + supply + reset_supply == departures + collection + reset_collection
        records.append({"station_key": keys[begin], "day": days[begin], "city": cities[begin],
                        "docks": capacity, "departures": departures, "arrivals": arrivals,
                        "supply_bikes": supply, "collection_bikes": collection,
                        "reset_supply_bikes": reset_supply, "reset_collection_bikes": reset_collection,
                        "ebike_departures": int(ebikes[begin:end].sum())})
    daily = pd.DataFrame.from_records(records)
    if daily.empty:
        return daily, pd.DataFrame()
    daily["year"] = daily.day.dt.year
    daily["month"] = daily.day.dt.month
    fields = ["departures", "arrivals", "supply_bikes", "collection_bikes", "reset_supply_bikes",
              "reset_collection_bikes", "ebike_departures"]
    monthly = daily.groupby(["year", "month", "city"], as_index=False)[fields].sum()
    monthly["demand_bikes"] = monthly[["supply_bikes", "collection_bikes", "reset_supply_bikes", "reset_collection_bikes"]].sum(axis=1)
    monthly["ebike_share"] = np.divide(monthly.ebike_departures, monthly.departures,
                                        out=np.zeros(len(monthly)), where=monthly.departures.to_numpy() != 0)
    return daily, monthly
