"""Synthetic hand calculations for the inventory proxy and the ambiguous bike unit.

These examples never read or amend observed trip data. Expected hourly states and
daily corrections below are hand-entered, then checked against inventory_proxy.
"""
from __future__ import annotations

import pandas as pd

from .inventory import inventory_proxy


PROVENANCE = "SYNTHETIC HAND COUNT: invented stations and trips; not observed Bluebikes data"
COURSE_BIKES_PER_SHIFT = 120
SHIFTS_PER_WEEK = 6


def build_unit_examples() -> dict:
    """Return display-ready hand tables, existing-proxy results, and assumptions.

    Hourly states and reset counts are explicit expected values, independent of
    the inventory implementation. A disagreement raises AssertionError so a
    Notebook cannot silently present an incorrect hand-worked explanation.
    """
    stations = pd.DataFrame({"station_key": ["SYNTHETIC_A", "SYNTHETIC_B"],
                             "city": ["SYNTHETIC_CITY", "SYNTHETIC_CITY"], "docks": [4, 4]})
    # station, hour, departures, arrivals, opening stock, net, unconstrained stock,
    # within-hour supply, within-hour collection, closing stock.
    examples = [
        {
            "case": "synthetic_one_way",
            "description": "Four customer trips A to B in one hour",
            "steps": [("A", 8, 4, 0, 2, -4, -2, 2, 0, 0),
                      ("B", 8, 0, 4, 2, 4, 6, 0, 2, 4)],
            # station, dep, arr, supply, collection, reset supply, reset collection,
            # closing stock before reset.
            "daily": [("A", 4, 0, 2, 0, 2, 0, 0), ("B", 0, 4, 0, 2, 0, 2, 4)],
            "paired_relocations": 4,
            "pairing": "Two B-to-A pickups/deliveries during the day, plus two B-to-A resets; algebraic pairing only",
        },
        {
            "case": "synthetic_return_hour",
            "description": "Four A-to-B trips, then four B-to-A trips in the next hour",
            "steps": [("A", 8, 4, 0, 2, -4, -2, 2, 0, 0),
                      ("B", 8, 0, 4, 2, 4, 6, 0, 2, 4),
                      ("A", 9, 0, 4, 0, 4, 4, 0, 0, 4),
                      ("B", 9, 4, 0, 4, -4, 0, 0, 0, 0)],
            "daily": [("A", 4, 4, 2, 0, 0, 2, 4), ("B", 4, 4, 0, 2, 2, 0, 0)],
            "paired_relocations": 4,
            "pairing": "Two B-to-A pickups/deliveries during the day, plus two A-to-B resets; algebraic pairing only",
        },
        {
            "case": "synthetic_external_depot",
            "description": "Four departures from A; arrivals occur outside the two-station example",
            "steps": [("A", 8, 4, 0, 2, -4, -2, 2, 0, 0),
                      ("B", 8, 0, 0, 2, 0, 2, 0, 0, 2)],
            "daily": [("A", 4, 0, 2, 0, 2, 0, 0), ("B", 0, 0, 0, 0, 0, 0, 2)],
            "paired_relocations": None,
            "pairing": "Four local deliveries from an external depot; its pickup endpoints are outside the example",
        },
    ]
    columns = ["station", "hour_number", "departures", "arrivals", "opening_stock", "net_arrivals",
               "unconstrained_stock", "supply_bikes", "collection_bikes", "closing_stock"]
    expected_columns = ["station", "departures", "arrivals", "supply_bikes", "collection_bikes",
                        "reset_supply_bikes", "reset_collection_bikes", "closing_stock_before_reset"]
    hourly_tables, reset_tables, conservation_tables, summaries, conversions = [], [], [], [], []
    for example in examples:
        case = example["case"]
        steps = pd.DataFrame(example["steps"], columns=columns)
        steps.insert(0, "case", case)
        steps["station_key"] = "SYNTHETIC_" + steps.station
        steps["hour"] = pd.to_datetime("2026-01-01") + pd.to_timedelta(steps.hour_number, unit="h")
        steps["docks"] = 4
        hourly = steps[["station_key", "hour", "departures", "arrivals"]].copy()
        hourly["ebike_departures"] = 0
        actual, monthly = inventory_proxy(hourly, stations)
        expected = pd.DataFrame(example["daily"], columns=expected_columns)
        expected["station_key"] = "SYNTHETIC_" + expected.station
        expected = expected.set_index("station_key")
        actual = actual.set_index("station_key")
        for station_key in expected.index:
            for field in expected_columns[1:-1]:
                if int(actual.loc[station_key, field]) != int(expected.loc[station_key, field]):
                    raise AssertionError(f"{case}/{station_key}/{field} disagrees with hand calculation")
        total_handling = int(monthly.demand_bikes.sum())
        expected_handling = int(expected[["supply_bikes", "collection_bikes", "reset_supply_bikes", "reset_collection_bikes"]].to_numpy().sum())
        if total_handling != expected_handling:
            raise AssertionError(f"{case} handling total disagrees with hand calculation")
        actual = actual.reset_index()
        actual["case"] = case
        actual = actual.merge(expected[["closing_stock_before_reset"]].reset_index(), on="station_key", validate="one_to_one")
        actual["initial_stock"] = actual.docks // 2
        actual["final_stock_after_reset"] = actual.initial_stock
        actual["conservation_lhs"] = actual.initial_stock + actual.arrivals + actual.supply_bikes + actual.reset_supply_bikes
        actual["conservation_rhs"] = actual.final_stock_after_reset + actual.departures + actual.collection_bikes + actual.reset_collection_bikes
        actual["balanced"] = actual.conservation_lhs.eq(actual.conservation_rhs)
        actual["customer_net_arrivals"] = actual.arrivals - actual.departures
        actual["handling_actions"] = actual[["supply_bikes", "collection_bikes", "reset_supply_bikes", "reset_collection_bikes"]].sum(axis=1)
        actual["matches_existing_proxy"] = True
        hourly_tables.append(steps.drop(columns="hour_number"))
        reset_tables.append(actual[["case", "station_key", "closing_stock_before_reset", "final_stock_after_reset",
                                    "reset_supply_bikes", "reset_collection_bikes"]])
        conservation_tables.append(actual[["case", "station_key", "initial_stock", "departures", "arrivals",
            "supply_bikes", "collection_bikes", "reset_supply_bikes", "reset_collection_bikes", "final_stock_after_reset",
            "customer_net_arrivals", "handling_actions", "conservation_lhs", "conservation_rhs", "balanced", "matches_existing_proxy"]])
        summary = {"case": case, "description": example["description"], "departures": int(actual.departures.sum()),
                   "arrivals": int(actual.arrivals.sum()), "within_day_supply": int(actual.supply_bikes.sum()),
                   "within_day_collection": int(actual.collection_bikes.sum()), "reset_supply": int(actual.reset_supply_bikes.sum()),
                   "reset_collection": int(actual.reset_collection_bikes.sum()), "handling_actions": total_handling,
                   "assumed_paired_relocations": example["paired_relocations"], "pairing_assumption": example["pairing"]}
        summaries.append(summary)
        for factor, interpretation in [(1, "120 handling actions per shift"), (2, "120 paired completed relocations per shift")]:
            course_units = total_handling if factor == 1 else example["paired_relocations"]
            conversions.append({"case": case, "endpoint_capacity_factor": factor, "interpretation": interpretation,
                                "course_bikes_per_shift": COURSE_BIKES_PER_SHIFT, "handling_actions": total_handling,
                                "assumed_course_units_demand": course_units,
                                "required_crew_shifts": None if course_units is None else course_units / COURSE_BIKES_PER_SHIFT,
                                "valid_for_this_hand_example": course_units is not None})
    summary_table = pd.DataFrame(summaries)
    summary_table["assumed_paired_relocations"] = summary_table.assumed_paired_relocations.astype("Int64")
    monthly_course_units = COURSE_BIKES_PER_SHIFT * SHIFTS_PER_WEEK * 31 / 7
    monthly_capacity = pd.DataFrame([
        {"month": "2026-01", "calendar_days": 31, "course_bikes_per_shift": COURSE_BIKES_PER_SHIFT,
         "shifts_per_week": SHIFTS_PER_WEEK, "average_crew_shifts": SHIFTS_PER_WEEK * 31 / 7,
         "endpoint_capacity_factor": factor, "monthly_course_bike_capacity": monthly_course_units,
         "monthly_handling_capacity": monthly_course_units * factor,
         "assumption": "Course bike means one handling action" if factor == 1 else "Course bike means one completed relocation with two included endpoints"}
        for factor in [1, 2]])
    return {
        "provenance": PROVENANCE,
        "hourly_steps": pd.concat(hourly_tables, ignore_index=True),
        "daily_reset": pd.concat(reset_tables, ignore_index=True),
        "station_conservation": pd.concat(conservation_tables, ignore_index=True),
        "case_summary": summary_table,
        "unit_conversion": pd.DataFrame(conversions),
        "monthly_capacity": monthly_capacity,
        "assumptions": [
            "All stations and trips in these tables are invented synthetic hand-count examples, separate from observed data.",
            "Each station starts at floor(docks/2); arrivals and departures are netted within each local hour.",
            "The proxy counts each supplied or collected bike as one handling action, including the daily half-full reset.",
            "A paired pickup plus delivery is two handling actions for one completed relocation; pairing here is an explicit algebraic assumption.",
            "Within-hour order, routes, truck inventory, depot inventory, travel time and feasible pickup-before-delivery schedules are not established.",
            "Unbalanced local supplies/collections require an external depot; dividing their sum by two does not establish an empirical relocation count.",
            "The course specification remains 120 bikes/shift and 6 shifts/week in both interpretations; only the meaning of bike and endpoint capacity factor changes.",
            "Monthly capacity uses calendar days/7 as an average workweek, so fractional shifts are planning averages, not a shift roster.",
        ],
    }
