"""Synthetic display arithmetic; no API/model calls and no persisted outputs."""
from copy import deepcopy
from io import BytesIO
import json
import unittest

import matplotlib.pyplot as plt
import numpy as np

from bluebikes.presentation import render_result


def sample(conversion=1, unchanged=False):
    chain = []
    for month in range(1, 13):
        event = month in (4, 5)
        demand = 1000 + 10 * month
        added = 0 if unchanged else (100 if event else 0)
        cap = 980
        newcap = 980 if unchanged or not event else 1100
        ft = 2 if unchanged or not event else 3
        chain.append({
            "year": 2026, "month": month, "city": "Other cities (shared)",
            "full_time_base": 2, "full_time_scenario": ft,
            "seasonal_base": 1, "seasonal_scenario": 1,
            "crew_cost_base": 19800, "crew_cost_scenario": 19800 if ft == 2 else 25800,
            "demand_bikes_base": demand / conversion,
            "demand_bikes_scenario": (demand + added) / conversion,
            "demand_handling_actions_base": demand,
            "demand_handling_actions_scenario": demand + added,
            "capacity_handling_actions_base": cap, "capacity_handling_actions_scenario": newcap,
            "uncovered_handling_actions_base": max(0, demand-cap),
            "uncovered_handling_actions_scenario": max(0, demand+added-newcap),
            "hire_decision_month_for_active_month": "No prior decision" if month == 1 else f"2026-{month-1:02d}",
            "prior_month_hires_decision_base": 0,
            "prior_month_hires_decision_scenario": 1 if month == 4 and not unchanged else 0,
        })
    periods = []
    for months in [12, 9]:
        for scenario, cost in [("initial_crews", 1000), ("no_event", 2000), ("reviewed_event", 3000)]:
            periods.append({"scenario": scenario, "period_months": months,
                            "crew_cash_cost_in_period": cost * months,
                            "uncovered_handling_actions": 1234.5,
                            "peak_full_time_crews_in_period": 2,
                            "peak_seasonal_crews_in_period": 1,
                            "peak_total_crews_in_period": 3,
                            "mandatory_seasonal_tail_cost_2027_separate": 7800 if months == 12 else None})
    return {
        "summary": {"selected_city": "Malden", "selected_group": "Other cities (shared)",
                    "handling_actions_per_course_bike": conversion,
                    "increment_handling_actions_per_event": 0 if unchanged else 3000},
        "monthly_chain": chain,
        "city_month_inputs": [{"year": 2026, "month": m,
                              "event_increment_handling_actions": 0 if unchanged else 1500} for m in [4, 5]],
        "period_comparison": periods,
    }


class PresentationTests(unittest.TestCase):
    def test_empty_invalid_or_unknown_result_clears_every_view(self):
        for value in [None, {}, {"summary": None}, {"summary": {"selected_city": None}},
                      {"summary": {"selected_city": "Malden", "selected_group": "Other"}, "monthly_chain": []}]:
            view = render_result(value)
            self.assertIsNone(view["crew_figure"])
            self.assertIsNone(view["demand_figure"])
            self.assertEqual(view["kpi_html"], "")
            self.assertTrue(view["monthly_table"].empty)

    def test_all_event_months_kpis_and_hiring_month_are_visible(self):
        view = render_result(sample())
        html = view["kpi_html"]
        self.assertIn("Malden / April 2026", html)
        self.assertIn("Malden / May 2026", html)
        self.assertEqual(html.count("<section "), 2)
        self.assertIn("March 2026", html)
        self.assertIn("$19,800", html)
        self.assertIn("$25,800", html)
        self.assertIn('class="bb-metric-value"', html)
        self.assertEqual(html.count('class="bb-metric-grid"'), 2)
        self.assertEqual(html.count('class="bb-metric-value"'), 6)
        self.assertIn("font-size:1.6rem", html)
        self.assertIn("Crew counts apply to shared group: Other cities (shared)", html)
        january = sample()
        january["city_month_inputs"] = [{"year": 2026, "month": 1}]
        self.assertIn("No prior decision", render_result(january)["kpi_html"])
        self.assertEqual(len(view["crew_figure"].axes[0].patches), 2)
        self.assertTrue(all(len(ax.patches) == 2 for ax in view["demand_figure"].axes))
        self.assertEqual(len(view["monthly_table"]), 12)
        self.assertLessEqual(len(view["monthly_table"].columns), 6)

    def test_conversion_one_and_two_plot_same_explicit_handling_fields(self):
        for factor in [1, 2]:
            data = sample(factor)
            figure = render_result(data)["demand_figure"]
            np.testing.assert_array_equal(figure.axes[0].lines[0].get_ydata(),
                                          [row["demand_handling_actions_base"] for row in data["monthly_chain"]])
            np.testing.assert_array_equal(figure.axes[1].lines[0].get_ydata(),
                                          [row["demand_handling_actions_scenario"] for row in data["monthly_chain"]])
            prior = next(line for line in figure.axes[1].lines if line.get_label() == "Prior-plan capacity")
            np.testing.assert_array_equal(prior.get_ydata(),
                                          [row["capacity_handling_actions_base"] for row in data["monthly_chain"]])
            self.assertEqual(prior.get_linestyle(), ":")
            self.assertEqual(len(figure.axes[1].texts), 1)
            self.assertEqual(figure.axes[1].texts[0].get_text(), "New demand 1,140 / Prior capacity 980")
            if factor == 2:
                self.assertNotEqual(figure.axes[0].lines[0].get_ydata()[0], data["monthly_chain"][0]["demand_bikes_base"])
            self.assertTrue(all(ax.get_ylabel() == "Handling actions" for ax in figure.axes))

    def test_uncovered_fill_exists_above_capacity_not_for_spare_capacity(self):
        figure = render_result(sample())["demand_figure"]
        self.assertTrue(figure.axes[0].collections[0].get_paths())
        empty = sample()
        for row in empty["monthly_chain"]:
            row["capacity_handling_actions_base"] = row["demand_handling_actions_base"] + 100
            row["capacity_handling_actions_scenario"] = row["demand_handling_actions_scenario"] + 100
        figure = render_result(empty)["demand_figure"]
        self.assertEqual(len(figure.axes[0].collections[0].get_paths()), 0)
        self.assertEqual(len(figure.axes[1].collections[0].get_paths()), 0)

    def test_zero_increment_and_zero_staffing_change_are_explicit(self):
        view = render_result(sample(unchanged=True))
        self.assertIn("No crew or monthly cash-cost change.", view["kpi_html"])
        self.assertIn("2 &rarr; 2", view["kpi_html"])
        self.assertIn("**0 handling actions per event**", view["explanation_md"])
        # Calendar highlights remain source-month highlights, not invented uplift.
        self.assertEqual(len(view["crew_figure"].axes[0].patches), 2)

    def test_city_group_scope_escaped_labels_and_separate_periods(self):
        data = sample()
        data["summary"]["selected_city"] = '<script>alert("x")</script>'
        data["summary"]["selected_group"] = "<b>shared group</b>"
        view = render_result(data)
        self.assertNotIn("<script>", view["kpi_html"])
        self.assertNotIn("<b>shared group</b>", view["kpi_html"])
        self.assertIn("&lt;script&gt;", view["kpi_html"])
        self.assertIn("whole system", view["explanation_md"])
        self.assertIn("not dedicated city crews", view["explanation_md"])
        self.assertEqual(view["annual_table"].iloc[0]["Cash cost"], "$12,000")
        self.assertEqual(view["backtest_table"].iloc[0]["Cash cost"], "$9,000")
        self.assertEqual(view["annual_table"].iloc[0]["2027 seasonal tail (separate)"], "$7,800")
        self.assertNotIn("2027 seasonal tail (separate)", view["backtest_table"].columns)

    def test_pure_no_mutation_figures_closed_and_serializable_by_matplotlib(self):
        data = sample()
        before = deepcopy(data)
        figures_before = plt.get_fignums()
        view = render_result(data)
        self.assertEqual(data, before)
        self.assertEqual(plt.get_fignums(), figures_before)
        for name in ["crew_figure", "demand_figure"]:
            output = BytesIO()
            view[name].savefig(output, format="png")
            self.assertGreater(len(output.getvalue()), 1000)
        self.assertEqual(len(view["crew_figure"].axes[0].lines), 4)
        self.assertIn("not lost trips", view["explanation_md"])
        self.assertIn("not an OpenAI output", view["explanation_md"])


if __name__ == "__main__":
    unittest.main()
