from fractions import Fraction
import unittest

import pandas as pd

from bluebikes.unit_examples import build_unit_examples


class UnitExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.examples = build_unit_examples()

    def test_one_way_hand_count_includes_boundary_and_reset(self):
        rows = self.examples["station_conservation"].query("case == 'synthetic_one_way'").set_index("station_key")
        self.assertEqual(rows.loc["SYNTHETIC_A", "supply_bikes"], 2)
        self.assertEqual(rows.loc["SYNTHETIC_A", "reset_supply_bikes"], 2)
        self.assertEqual(rows.loc["SYNTHETIC_B", "collection_bikes"], 2)
        self.assertEqual(rows.loc["SYNTHETIC_B", "reset_collection_bikes"], 2)
        case = self.examples["case_summary"].set_index("case").loc["synthetic_one_way"]
        self.assertEqual(case.handling_actions, 8)
        self.assertEqual(case.assumed_paired_relocations, 4)
        steps = self.examples["hourly_steps"].query("case == 'synthetic_one_way'").set_index("station_key")
        self.assertEqual(steps.loc["SYNTHETIC_A", "unconstrained_stock"], -2)
        self.assertEqual(steps.loc["SYNTHETIC_A", "closing_stock"], 0)
        self.assertEqual(steps.loc["SYNTHETIC_B", "unconstrained_stock"], 6)
        self.assertEqual(steps.loc["SYNTHETIC_B", "closing_stock"], 4)

    def test_zero_station_net_can_have_positive_rebalancing_work(self):
        rows = self.examples["station_conservation"].query("case == 'synthetic_return_hour'")
        self.assertEqual(rows.customer_net_arrivals.tolist(), [0, 0])
        self.assertEqual(rows.handling_actions.tolist(), [4, 4])

    def test_unbalanced_depot_case_has_no_supported_divide_by_two(self):
        case = self.examples["case_summary"].set_index("case").loc["synthetic_external_depot"]
        self.assertEqual(case.handling_actions, 4)
        self.assertEqual(case.within_day_supply + case.reset_supply, 4)
        self.assertEqual(case.within_day_collection + case.reset_collection, 0)
        self.assertTrue(pd.isna(case.assumed_paired_relocations))
        conversion = self.examples["unit_conversion"].query("case == 'synthetic_external_depot' and endpoint_capacity_factor == 2").iloc[0]
        self.assertFalse(conversion.valid_for_this_hand_example)
        self.assertTrue(pd.isna(conversion.required_crew_shifts))

    def test_each_station_conserves_inventory_after_reset(self):
        rows = self.examples["station_conservation"]
        self.assertEqual(len(rows), 6)
        self.assertTrue(rows.balanced.all())
        self.assertTrue(rows.matches_existing_proxy.all())
        self.assertEqual(rows.conservation_lhs.tolist(), rows.conservation_rhs.tolist())

    def test_capacity_conversion_preserves_course120_specification(self):
        capacity = self.examples["monthly_capacity"].set_index("endpoint_capacity_factor")
        expected = float(Fraction(22320, 7))  #120 bikes/shift *6 shifts/week *31 days /7.
        self.assertEqual(capacity.course_bikes_per_shift.tolist(), [120, 120])
        self.assertAlmostEqual(capacity.loc[1, "monthly_course_bike_capacity"], expected)
        self.assertAlmostEqual(capacity.loc[2, "monthly_course_bike_capacity"], expected)
        self.assertAlmostEqual(capacity.loc[1, "monthly_handling_capacity"], expected)
        self.assertAlmostEqual(capacity.loc[2, "monthly_handling_capacity"], 2 * expected)
        conversions = self.examples["unit_conversion"].query("case == 'synthetic_one_way'").set_index("endpoint_capacity_factor")
        self.assertAlmostEqual(conversions.loc[1, "required_crew_shifts"], 8 / 120)
        self.assertAlmostEqual(conversions.loc[2, "required_crew_shifts"], 4 / 120)


if __name__ == "__main__":
    unittest.main()
