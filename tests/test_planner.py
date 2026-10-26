import unittest
import numpy as np
import pandas as pd

from bluebikes.planner import (
    PlannerConfig, capacity_per_crew, plan_crews, baseline_plan,
    evaluate_plan, allocate_city_capacity, _decorate,
)


def demands(cities=("Boston",), amount=0):
    return pd.DataFrame([{"year": 2026, "month": m, "city": c, "demand_bikes": float(amount)} for c in cities for m in range(1, 13)])


class PlannerTests(unittest.TestCase):
    def test_capacity_calendar_and_cost(self):
        self.assertAlmostEqual(capacity_per_crew(2026, 2), 2880)
        self.assertAlmostEqual(capacity_per_crew(2026, 1), 120 * 6 * 31 / 7)
        self.assertAlmostEqual(0.40 * 0 + 0.45 * 3.25 + 0.15 * (3.25 + 25), 5.70)
        p, summary = baseline_plan(demands())
        self.assertEqual(p.loc[p.month == 1, "full_time"].sum(), 14)
        self.assertEqual(summary["crew_cost_2026"], 14 * 12 * 6000)
        self.assertEqual(summary["terminal_seasonal_committed_cost_2027"], 0)

    def test_one_month_hire_lead(self):
        d = demands(amount=5000)
        cfg = PlannerConfig(initial_ft={"Boston": 0}, pool_other_cities=False,
                            seasonal_system_cap=0, affected_users_per_proxy_bike=100)
        p, _ = plan_crews(d, cfg)
        self.assertEqual(int(p.loc[p.month == 1, "full_time"].iloc[0]), 0)
        self.assertEqual(int(p.loc[p.month == 1, "hires_effective"].iloc[0]), 0)
        self.assertEqual(int(p.loc[p.month == 1, "hires_decision"].iloc[0]), 2)
        self.assertEqual(int(p.loc[p.month == 2, "hires_effective"].iloc[0]), 2)
        self.assertEqual(int(p.loc[p.month == 2, "full_time"].iloc[0]), 2)

    def test_one_month_firing_notice_and_severance(self):
        cfg = PlannerConfig(initial_ft={"Boston": 1}, pool_other_cities=False, seasonal_system_cap=0)
        p, summary = plan_crews(demands(), cfg)
        self.assertEqual(int(p.loc[p.month == 1, "full_time"].iloc[0]), 1)
        self.assertEqual(int(p.loc[p.month == 1, "fires_notice"].iloc[0]), 1)
        self.assertEqual(int(p.loc[p.month == 2, "fires_effective"].iloc[0]), 1)
        self.assertEqual(int(p.loc[p.month == 2, "full_time"].iloc[0]), 0)
        self.assertAlmostEqual(summary["crew_cost_2026"], 6000 + 13500)

    def test_seasonal_minimum_three_and_system_cap(self):
        d = demands(("Boston", "Cambridge"))
        d.loc[d.month == 2, "demand_bikes"] = 100000
        cfg = PlannerConfig(initial_ft={"Boston": 0, "Cambridge": 0}, pool_other_cities=False,
                            ft_monthly_cost=1e9, affected_users_per_proxy_bike=100)
        p, summary = plan_crews(d, cfg)
        monthly = p.groupby("month").seasonal.sum()
        self.assertEqual(monthly.loc[1], 0)
        self.assertEqual(monthly.loc[2], 8)
        self.assertEqual(monthly.loc[3], 8)
        self.assertEqual(monthly.loc[4], 8)
        self.assertEqual(monthly.loc[5], 0)
        self.assertTrue((monthly <= 8).all())
        self.assertEqual(summary["crew_cost_2026"], 8 * 3 * 7800)
        # Reconstruct FIFO ages independently to check aggregate duration logic.
        for _, city in p.groupby("city"):
            cohorts = []
            for row in city.itertuples():
                ends = row.seasonal_ends
                while ends:
                    start, count = cohorts[0]
                    self.assertGreaterEqual(row.month - start, 3)
                    removed = min(ends, count)
                    ends -= removed
                    count -= removed
                    if count:
                        cohorts[0] = (start, count)
                    else:
                        cohorts.pop(0)
                if row.seasonal_starts:
                    cohorts.append((row.month, row.seasonal_starts))

    def test_terminal_november_december_obligations(self):
        p = demands()
        for col in ("full_time", "hires_effective", "fires_effective", "seasonal", "seasonal_starts", "seasonal_ends"):
            p[col] = 0
        p.loc[p.month == 11, ["seasonal", "seasonal_starts"]] = [1, 1]
        p.loc[p.month == 12, ["seasonal", "seasonal_starts"]] = [2, 1]
        p, summary = _decorate(p, PlannerConfig())
        self.assertEqual(p.loc[p.month == 11, "terminal_seasonal_months"].iloc[0], 1)
        self.assertEqual(p.loc[p.month == 12, "terminal_seasonal_months"].iloc[0], 2)
        self.assertEqual(summary["crew_cost_2026"], 3 * 7800)
        self.assertEqual(summary["terminal_seasonal_committed_cost_2027"], 3 * 7800)
        self.assertEqual(summary["total_committed_crew_cost"], 6 * 7800)

    def test_frozen_evaluation_and_city_share_conservation(self):
        d = demands(("Boston", "Everett", "Malden"), amount=1000)
        p, _ = baseline_plan(d)
        allocation = allocate_city_capacity(p, d)
        self.assertEqual(len(allocation), 36)
        other = allocation[allocation.city != "Boston"]
        self.assertTrue((other.groupby("month").full_time_capacity_share.sum() == 2).all())
        self.assertTrue((other.groupby("month").allocated_crew_cost.sum() == 12000).all())
        a = d[d.month <= 9].copy()
        a["demand_bikes"] *= 50
        original = p.copy(deep=True)
        evaluation = evaluate_plan(p, a)
        self.assertEqual(len(evaluation), 18)  # Boston plus shared group, nine months.
        self.assertTrue((evaluation.actual_unmet_bikes >= 0).all())
        pd.testing.assert_frame_equal(p, original)

    def test_bad_input_rejected_and_no_loss_is_not_proxy_times_570(self):
        with self.assertRaises(ValueError):
            plan_crews(demands().iloc[:-1])
        cfg = PlannerConfig(affected_users_per_proxy_bike=0)
        p, summary = baseline_plan(demands(amount=1e6), cfg)
        self.assertGreater(summary["unmet_proxy_bikes"], 0)
        self.assertEqual(summary["assumed_service_loss"], 0)
        self.assertEqual(summary["assumed_affected_users_per_proxy_bike"], 0)

    def test_capacity_sensitivity_changes_service_without_replanning(self):
        d = demands(amount=100000)
        cfg = PlannerConfig(initial_ft={"Boston": 1}, pool_other_cities=False)
        p, _ = baseline_plan(d, cfg)
        normal = evaluate_plan(p, d, cfg)
        stressed = evaluate_plan(p, d, PlannerConfig(initial_ft={"Boston": 1}, pool_other_cities=False, bikes_per_shift=108))
        np.testing.assert_allclose(stressed.capacity_bikes, normal.capacity_bikes * .9)
        self.assertGreater(stressed.actual_unmet_bikes.sum(), normal.actual_unmet_bikes.sum())
        np.testing.assert_array_equal(stressed.full_time, normal.full_time)

    def test_dedicated_initial_allocation_rejects_invalid_cities_and_counts(self):
        d = demands(("Boston", "Everett", "Malden"))
        bad_allocations = [
            {"Boston": 2}, {"Unknown city": 2},
            {"Everett": 1.5, "Malden": .5},
            {"Everett": -1, "Malden": 3},
            {"Everett": True, "Malden": 1}, {"Everett": 1},
        ]
        for allocation in bad_allocations:
            with self.subTest(allocation=allocation), self.assertRaises(ValueError):
                baseline_plan(d, PlannerConfig(pool_other_cities=False, dedicated_other_initial=allocation))
        p, _ = baseline_plan(d, PlannerConfig(pool_other_cities=False, dedicated_other_initial={"Everett": 1, "Malden": 1}))
        january = p[p.month == 1].set_index("city")
        self.assertEqual(january.loc["Everett", "full_time"], 1)
        self.assertEqual(january.loc["Malden", "full_time"], 1)
        self.assertEqual(january.full_time.sum(), 14)


if __name__ == "__main__":
    unittest.main()
