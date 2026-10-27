"""Offline coordinate-display tests; no API, optimizer or source-file writes."""
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bluebikes.geography import AREA_PER_CREW, _load_cached, geographic_result_from_chain, load_stations, render_geography
from bluebikes.planner import CORE_CITIES, OTHER_POOL

ROOT = Path(__file__).resolve().parents[1]


def station_fixture():
    cities = list(CORE_CITIES) + ["Arlington", "Chelsea", "Everett", "Malden", "Medford",
                                  "Newton", "Revere", "Salem", "Watertown"]
    rows = []
    for index, city in enumerate(cities):
        for offset in [0, .002]:
            rows.append({"name": city + str(offset), "city": city,
                         "latitude": 42.30 + index*.01 + offset,
                         "longitude": -71.18 + index*.008 + offset,
                         "docks": 10, "valid_coordinates": True})
    return pd.DataFrame(rows)


def result_fixture(conversion=1, zero=False):
    base, scenario = [], []
    crews = {"Boston": 6, "Cambridge": 4, "Somerville": 1, "Brookline": 1, OTHER_POOL: 2}
    for month in range(1, 13):
        for city, ft in crews.items():
            old = {"year": 2026, "month": month, "city": city, "full_time": 0 if zero else ft,
                   "seasonal": 0, "demand_bikes": 100}
            new = {**old}
            if not zero and city == "Boston":
                if month == 4:
                    new["full_time"] += 1
                if month == 7:
                    new["seasonal"] = 2
            base.append(old)
            scenario.append(new)
    return {"summary": {"handling_actions_per_course_bike": conversion},
            "geographic_plans": {"base": base, "scenario": scenario}}


def core_collection(ax, city):
    return next(c for c in ax.collections if c.get_label() == "_core_crews_" + city)


class GeographyTests(unittest.TestCase):
    def test_real_snapshot_cache_and_defensive_copy(self):
        _load_cached.cache_clear()
        reader = pd.read_csv
        with patch("bluebikes.geography.pd.read_csv", wraps=reader) as read:
            first, second = load_stations(ROOT), load_stations(ROOT)
            self.assertEqual(read.call_count, 1)
        self.assertEqual(len(first), 613)
        self.assertEqual(first.city.nunique(), 13)
        self.assertTrue(first.valid_coordinates.all())
        first.loc[0, "city"] = "mutated"
        self.assertNotEqual(load_stations(ROOT).loc[0, "city"], "mutated")
        pd.testing.assert_frame_equal(second, load_stations(ROOT))

    def test_same_axes_geographic_scale_and_bubble_area_across_months(self):
        stations, result = station_fixture(), result_fixture()
        april = render_geography(result, 4, stations)["figure"]
        july = render_geography(result, 7, stations)["figure"]
        for figure in [april, july]:
            left, right = figure.axes
            self.assertEqual(left.get_xlim(), right.get_xlim())
            self.assertEqual(left.get_ylim(), right.get_ylim())
            self.assertEqual(left.get_aspect(), right.get_aspect())
            self.assertEqual(left.get_xlim(), april.axes[0].get_xlim())
            self.assertEqual(left.get_ylim(), april.axes[0].get_ylim())
            self.assertEqual(core_collection(left, "Boston").get_sizes()[0], 6 * AREA_PER_CREW)
        self.assertEqual(core_collection(april.axes[1], "Boston").get_sizes()[0], 7 * AREA_PER_CREW)
        self.assertEqual(core_collection(july.axes[1], "Boston").get_sizes()[0], 8 * AREA_PER_CREW)
        self.assertEqual([text.get_text() for text in april.axes[1].get_legend().texts],
                         [text.get_text() for text in july.axes[1].get_legend().texts])

    def test_centroid_is_actual_station_mean_pool_is_text_only(self):
        stations = station_fixture()
        view = render_geography(result_fixture(), 4, stations)
        for ax in view["figure"].axes:
            labels = [c.get_label() for c in ax.collections]
            self.assertEqual(sum(label.startswith("_core_crews_") for label in labels), 4)
            self.assertFalse(any(OTHER_POOL in label for label in labels))
            expected = stations[stations.city == "Boston"][["longitude", "latitude"]].mean().to_numpy()
            np.testing.assert_allclose(core_collection(ax, "Boston").get_offsets()[0], expected)
        self.assertIn("FT 2 -> 2", view["pool_md"])
        self.assertIn("not one allocation per city", view["pool_md"])
        self.assertIn("not crew bases", view["note_md"])

    def test_zero_crews_and_no_change_are_not_faked(self):
        view = render_geography(result_fixture(zero=True), 1, station_fixture())
        for ax in view["figure"].axes:
            for city in CORE_CITIES:
                self.assertEqual(core_collection(ax, city).get_sizes()[0], 0)
            self.assertTrue(any("Total 0" in t.get_text() and "total +0" in t.get_text() for t in ax.texts))
        self.assertIn("total 0 -> 0 (change +0)", view["pool_md"])

    def test_conversion_changes_handling_context_not_crew_areas_or_120(self):
        stations = station_fixture()
        first = render_geography(result_fixture(1), 4, stations)
        second = render_geography(result_fixture(2), 4, stations)
        self.assertIn("100 -> 100 handling actions", first["pool_md"])
        self.assertIn("200 -> 200 handling actions", second["pool_md"])
        self.assertIn("Boston 200 -> 200", second["note_md"])
        self.assertIn("120 bikes/shift", second["note_md"])
        self.assertTrue(any("Proxy 100 actions" in text.get_text() for text in first["figure"].axes[0].texts))
        self.assertTrue(any("Proxy 200 actions" in text.get_text() for text in second["figure"].axes[0].texts))
        self.assertEqual(second["figure"].axes[1].get_legend().texts[0].get_text(), "1 crew")
        self.assertEqual(core_collection(first["figure"].axes[1], "Boston").get_sizes()[0],
                         core_collection(second["figure"].axes[1], "Boston").get_sizes()[0])

    def test_invalid_and_missing_coords_never_create_representative_points(self):
        stations = station_fixture()
        stations.loc[stations.city == "Boston", "latitude"] = np.nan
        view = render_geography(result_fixture(), 4, stations)
        for ax in view["figure"].axes:
            self.assertFalse(any(c.get_label() == "_core_crews_Boston" for c in ax.collections))
        self.assertIn("omitted, not relocated", view["note_md"])
        self.assertIn("Boston", view["note_md"])
        for month in [None, 0, 13, True, 4.5, "4"]:
            blank = render_geography(result_fixture(), month, stations)
            self.assertIsNone(blank["figure"])
            self.assertEqual(blank["pool_md"], "")
            self.assertEqual(blank["note_md"], "")
        self.assertIsNone(render_geography(None, 4, stations)["figure"])
        self.assertIsNone(render_geography({"geographic_plans": {"base": "bad"}}, 4, stations)["figure"])
        stations["latitude"] = np.nan
        self.assertIsNone(render_geography(result_fixture(), 4, stations)["figure"])

    def test_saved_focused_chain_reshape_preserves_actual_counts_and_units(self):
        chain = pd.read_csv(ROOT / "results/focused_event_chain.csv")
        original = chain.copy(deep=True)
        result = geographic_result_from_chain(chain)
        before = next(row for row in result["geographic_plans"]["base"] if row["city"] == "Boston" and row["month"] == 4)
        after = next(row for row in result["geographic_plans"]["scenario"] if row["city"] == "Boston" and row["month"] == 4)
        self.assertEqual(before["full_time"], 12)
        self.assertEqual(after["full_time"], 13)
        self.assertAlmostEqual(after["demand_bikes"] - before["demand_bikes"], 3000)
        pd.testing.assert_frame_equal(chain, original)
        # Passing conversion2 labels already-converted planner units; helper
        # never silently divides a saved chain or changes its crew decisions.
        converted = geographic_result_from_chain(chain, conversion=2)
        self.assertEqual(converted["geographic_plans"], result["geographic_plans"])
        self.assertEqual(converted["summary"]["handling_actions_per_course_bike"], 2)
        self.assertEqual(len(converted["geographic_plans"]["base"]), 60)

    def test_no_input_mutation_no_open_figures_and_png_serialization(self):
        stations, result = station_fixture(), result_fixture()
        before_stations, before_result = stations.copy(deep=True), deepcopy(result)
        figures = plt.get_fignums()
        view = render_geography(result, 4, stations)
        self.assertEqual(plt.get_fignums(), figures)
        self.assertEqual(result, before_result)
        pd.testing.assert_frame_equal(stations, before_stations)
        output = BytesIO()
        view["figure"].savefig(output, format="png")
        self.assertGreater(len(output.getvalue()), 1000)


if __name__ == "__main__":
    unittest.main()
