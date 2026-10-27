"""Synthetic scenario arithmetic; fixtures below are not API predictions."""
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from bluebikes.planner import PlannerConfig, baseline_plan, plan_crews
from bluebikes.scenarios import generate_review_scenarios, _course_input, _period_row

ROOT = Path(__file__).resolve().parents[1]


class ScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forecast = pd.DataFrame([
            {"year": 2026, "month": m, "city": "Boston", "demand_bikes": 5000.0}
            for m in range(1, 13)])
        cls.actual = cls.forecast[cls.forecast.month <= 9].copy()
        cls.cfg = PlannerConfig(initial_ft={"Boston": 1}, pool_other_cities=False,
                                seasonal_system_cap=0, affected_users_per_proxy_bike=100)
        cls.baseline, _ = baseline_plan(cls.forecast, cls.cfg)
        cls.proposal, _ = plan_crews(cls.forecast, cls.cfg)
        docs = json.loads((ROOT / "fixtures/event_documents.json").read_text(encoding="utf-8"))
        cls.fixture_events = [doc["human_gold"] for doc in docs]
        cls.result = generate_review_scenarios(
            cls.forecast, {"events": cls.fixture_events, "mode": "fixture",
                           "live_llm_verified": False}, cls.actual,
            cls.baseline, cls.proposal, cls.cfg)

    def test_two_endpoint_actions_to_course_bike_conversion(self):
        # One bike picked up then delivered = two handling actions, one complete
        # relocation under factor2. The course still specifies120bikes/shift.
        d = pd.DataFrame({"demand_bikes": [2.0]})
        self.assertEqual(_course_input(d, 1).demand_bikes.iloc[0], 2)
        self.assertEqual(_course_input(d, 2).demand_bikes.iloc[0], 1)
        self.assertEqual(d.demand_bikes.iloc[0], 2)
        groups = self.result["tables"]["unit_group_month_comparison"]
        self.assertTrue(groups.course_bikes_per_shift.eq(120).all())
        january = groups[groups.month == 1]
        np.testing.assert_allclose(january.capacity_per_crew, 120 * 6 * 31 / 7)
        np.testing.assert_allclose(groups.capacity_handling_actions,
                                   groups.capacity_course_bike_units * groups.handling_actions_per_course_bike)

    def test_real_named_event_fixture_flows_to_april_only(self):
        chain = self.result["tables"]["focused_event_chain"]
        april = chain[chain.month == 4].iloc[0]
        self.assertEqual(april.event_increment_handling_actions, 3000)
        self.assertEqual(april.demand_bikes_change, 3000)
        self.assertEqual(chain.demand_bikes_change.sum(), 3000)
        self.assertIn("baa.org", april.source_urls)
        # First-year staffing lead is preserved despite an event stress case.
        self.assertEqual(chain.loc[chain.month == 1, "full_time_scenario"].iloc[0], 1)
        self.assertTrue(self.result["metadata"]["focused_event_found"])
        exclusions = self.result["tables"]["event_exclusions"]
        hocr = exclusions[exclusions.event_name.str.contains("Charles")].iloc[0]
        self.assertEqual(hocr.status, "excluded_missing_city_no_location_inference")
        self.assertEqual(hocr.event_increment_handling_actions, 0)

    def test_matched_horizons_and_separate_tail(self):
        table = self.result["tables"]["scenario_period_comparison"]
        initial = table[table.scenario == "initial_crews_factor1"].set_index("period_months")
        self.assertEqual(initial.loc[12, "crew_cash_cost_in_period"], 12 * 6000)
        self.assertEqual(initial.loc[9, "crew_cash_cost_in_period"], 9 * 6000)
        self.assertEqual(initial.loc[12, "mandatory_seasonal_tail_cost_2027_separate"], 0)
        self.assertTrue(pd.isna(initial.loc[9, "mandatory_seasonal_tail_cost_2027_separate"]))
        proposed = table[table.scenario == "proposal_no_event_factor1"].set_index("period_months")
        self.assertEqual(proposed.loc[12, "crew_cash_cost_in_period"], 6000 + 11 * 12000)
        self.assertEqual(proposed.loc[9, "crew_cash_cost_in_period"], 6000 + 8 * 12000)
        self.assertEqual(proposed.loc[9, "demand_handling_actions"], self.actual.demand_bikes.sum())

    def test_factor_two_replans_crews_without_halving_handling_penalty(self):
        groups = self.result["tables"]["unit_group_month_comparison"]
        first = groups[groups.handling_actions_per_course_bike == 1]
        second = groups[groups.handling_actions_per_course_bike == 2]
        self.assertGreater(first.full_time.sum(), second.full_time.sum())
        self.assertGreater(first.crew_cost.sum(), second.crew_cost.sum())
        np.testing.assert_allclose(first.demand_handling_actions, second.demand_handling_actions)
        self.assertTrue(groups.assumed_users_per_uncovered_handling_action.eq(100).all())
        np.testing.assert_allclose(groups.assumed_service_loss,
                                   groups.uncovered_handling_actions * 100 * 5.70)
        self.assertEqual(second.loc[second.month == 1, "full_time"].iloc[0], 1)

    def test_actual_poisoning_does_not_change_any_forecast_plan(self):
        poisoned = self.actual.copy()
        poisoned["demand_bikes"] = 1e9
        result = generate_review_scenarios(
            self.forecast, self.fixture_events, poisoned, self.baseline, self.proposal, self.cfg)
        for name in ["focused_event_chain", "calendar_event_chain", "unit_group_month_comparison"]:
            pd.testing.assert_frame_equal(result["tables"][name], self.result["tables"][name])
        original = self.result["tables"]["scenario_period_comparison"]
        new = result["tables"]["scenario_period_comparison"]
        pd.testing.assert_frame_equal(original[original.period_months == 12].reset_index(drop=True),
                                      new[new.period_months == 12].reset_index(drop=True))
        self.assertGreater(new[new.period_months == 9].uncovered_handling_actions.sum(),
                           original[original.period_months == 9].uncovered_handling_actions.sum())

    def test_peak_crews_sum_across_groups_before_monthly_maximum(self):
        forecast = pd.concat([self.forecast, self.forecast.assign(city="Cambridge")], ignore_index=True)
        cfg = PlannerConfig(initial_ft={"Boston": 1, "Cambridge": 1}, pool_other_cities=False)
        plan, _ = baseline_plan(forecast, cfg)
        # Two dedicated groups, each one crew: the system peak is two, not row max one.
        annual, observed = _period_row(plan, forecast[forecast.month <= 9], "handcount", 1, cfg)
        self.assertEqual(plan.full_time.max(), 1)
        for row in [annual, observed]:
            self.assertEqual(row["peak_full_time_crews_in_period"], 2)
            self.assertEqual(row["peak_seasonal_crews_in_period"], 0)
            self.assertEqual(row["peak_total_crews_in_period"], 2)
            self.assertEqual(row["ending_full_time_crews_in_period"], 2)

    def test_metadata_is_strict_json_and_excluded_missing_values_are_null(self):
        encoded = json.dumps(self.result["metadata"], allow_nan=False)
        decoded = json.loads(encoded)
        hocr = next(row for row in decoded["excluded_events"] if "Charles" in row["event_name"])
        self.assertIsNone(hocr["year"])
        self.assertIsNone(hocr["month"])
        self.assertIsNone(hocr["city"])

    def test_missing_month_and_changed_course_capacity_rejected(self):
        with self.assertRaises(ValueError):
            generate_review_scenarios(self.forecast, self.fixture_events, self.actual.iloc[:-1],
                                      self.baseline, self.proposal, self.cfg)
        with self.assertRaises(ValueError):
            generate_review_scenarios(self.forecast, self.fixture_events, self.actual,
                                      self.baseline, self.proposal, PlannerConfig(bikes_per_shift=240))


if __name__ == "__main__":
    unittest.main()
