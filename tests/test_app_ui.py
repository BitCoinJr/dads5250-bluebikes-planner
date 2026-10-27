"""Thin-screen workflow guards using real cached evidence and mocked live calls."""
from __future__ import annotations

import copy
from pathlib import Path
from unittest.mock import Mock, patch
import unittest

from bluebikes.app import ScreenActions, create_app, launch_local
from bluebikes.app_service import AppService

ROOT = Path(__file__).resolve().parents[1]


def form_values(state, *, edits=None, notes="SYNTHETIC TEST session confirmation"):
    document = state["document"]
    record = {**state["original_llm"], **(edits or {})}
    return [document["source_title"], document["source_url"], document["source_text"],
            record["start_date"] or "", record["end_date"] or "", record["city"] or "",
            record["location"] or "", record["expected_crowd_size"],
            "\n".join(record["ambiguities"]), notes]


def mock_plan():
    """A result-shaped stub; inventory/optimization are tested separately."""
    return {
        "period_comparison": [
            {"scenario": "initial_crews", "period": "2026-01 through 2026-12", "crew_cash_cost_in_period": 3},
            {"scenario": "no_event", "period": "2026-01 through 2026-12", "crew_cash_cost_in_period": 2},
            {"scenario": "reviewed_event", "period": "2026-01 through 2026-12", "crew_cash_cost_in_period": 4},
            {"scenario": "no_event", "period": "2026-01 through 2026-09", "crew_cash_cost_in_period": 1},
            {"scenario": "reviewed_event", "period": "2026-01 through 2026-09", "crew_cash_cost_in_period": 2},
        ],
        "monthly_chain": [{"month": 4, "city": "Boston", "full_time_base": 6,
                           "full_time_scenario": 7, "seasonal_base": 1, "seasonal_scenario": 2,
                           "crew_cost_base": 43800, "crew_cost_scenario": 57600,
                           "uncovered_handling_actions_base": 100, "uncovered_handling_actions_scenario": 0,
                           "prior_month_hires_decision_base": 0, "prior_month_hires_decision_scenario": 1,
                           "hire_decision_month_for_active_month": "2026-03"}],
        "city_month_inputs": [{"month": 4, "city": "Boston"}],
        "assumptions": ["SYNTHETIC TEST RESULT, not an operational calculation"],
        "summary": {"selected_city": "Boston", "selected_group": "Boston",
                    "handling_actions_per_course_bike": 1,
                    "increment_handling_actions_per_event": 3000},
    }


class ScreenWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.service = AppService(ROOT)
        self.actions = ScreenActions(self.service)
        self.state = self.service.select(self.service.choices()[0][1])
        self.assertEqual(self.state["status"], "saved_ready")
        self.assertIsNotNone(self.state["original_llm"])

    def assert_blank_result(self, output, *, disabled=True):
        self.assertIsNone(output[0]["result"])
        self.assertTrue(output[6].empty)
        self.assertTrue(output[7].empty)
        self.assertEqual(output[8], "")
        self.assertEqual(output[5]["interactive"], not disabled)

    def confirmed(self):
        output = self.actions.confirm(self.state, *form_values(self.state))
        self.assertEqual(len(output), 9)
        self.assertEqual(output[0]["status"], "review_confirmed")
        self.assertTrue(output[5]["interactive"])
        return output[0]

    def applied(self):
        state = self.confirmed()
        with patch.object(self.service, "_plan", return_value=mock_plan()) as planner:
            output = self.actions.apply(state, *form_values(state), 3000, 1)
        planner.assert_called_once()
        self.assertEqual(output[0]["status"], "plan_ready")
        self.assertFalse(output[6].empty)
        self.assertFalse(output[7].empty)
        # The screen compares the no-event plan with the reviewed-event plan;
        # the initial-crew benchmark remains in backend/audit data.
        self.assertEqual(set(output[6]["Scenario"]), {"No-event baseline", "Reviewed event"})
        self.assertEqual(set(zip(output[6]["Scenario"], output[6]["Period"])), {
            (scenario, period) for scenario in ("No-event baseline", "Reviewed event")
            for period in ("Jan-Dec 2026 forecast", "Jan-Sep 2026 observed proxy")})
        self.assertIn("Cash cost ($)", output[6].columns)
        self.assertEqual(list(output[7].columns), ["Month", "FT baseline", "FT event", "Seasonal baseline", "Seasonal event",
                                                  "Cost baseline ($)", "Cost event ($)", "Uncovered baseline actions", "Uncovered event actions"])
        self.assertIn("Month **4**", output[8])
        self.assertIn("Prior hiring decision month: **2026-03**", output[8])
        self.assertIn("hires **0 -> 1**", output[8])
        self.assertIn("next-month staffing", output[8])
        return output[0]

    def test_screen_builds_from_saved_evidence_without_provider_or_key_read(self):
        with patch("bluebikes.app_service.extract_event", side_effect=AssertionError("No API on screen construction")) as provider, \
                patch("bluebikes.app_service._project_env", side_effect=AssertionError("No key needed for saved mode")):
            app = create_app(ROOT)
        try:
            components = app.get_config_file()["components"]
            apply = next(component for component in components if component["type"] == "button"
                         and "Apply to plan" in component["props"].get("value", ""))
            self.assertFalse(apply["props"]["interactive"])
            choices = next(component for component in components if component["type"] == "dropdown")["props"]["choices"]
            self.assertEqual(len(choices), 7)
            original = next(component for component in components if component["type"] == "json"
                            and component["props"].get("label", "").startswith("Unedited LLM output"))
            self.assertEqual(original["props"]["value"]["event_name"], self.state["original_llm"]["event_name"])
            provider.assert_not_called()
        finally:
            app.close()

    def test_select_and_saved_callbacks_return_complete_form_with_apply_disabled(self):
        selected = self.actions.select(self.service.choices()[0][1])
        self.assertEqual(len(selected), 19)
        self.assertEqual(selected[3]["status"], "saved_ready")
        self.assertFalse(selected[8]["interactive"])
        document = self.state["document"]
        loaded = self.actions.saved(self.state, document["source_title"], document["source_url"], document["source_text"])
        self.assertEqual(len(loaded), 16)
        self.assert_blank_result(loaded)
        self.assertEqual(loaded[3]["mode"], "recorded")

    def test_apply_without_confirmation_cannot_invoke_planner(self):
        with patch.object(self.service, "_plan", side_effect=AssertionError("Review is required")) as planner:
            output = self.actions.apply(self.state, *form_values(self.state), 3000, 1)
        self.assertEqual(output[0]["status"], "apply_blocked")
        planner.assert_not_called()
        self.assert_blank_result(output)

    def test_input_and_review_callbacks_clear_old_results(self):
        state = self.applied()
        old_original = copy.deepcopy(state["original_llm"])
        document = state["document"]
        changed = self.actions.input_changed(state, document["source_title"], document["source_url"], document["source_text"] + " changed")
        self.assertEqual(len(changed), 16)
        self.assertEqual(changed[0]["status"], "input_changed")
        self.assertIsNone(changed[2])
        self.assertFalse(changed[3])
        self.assertIsNone(changed[4])
        self.assert_blank_result(changed)
        reviewed = self.actions.review_changed(state)
        self.assertEqual(reviewed[0]["status"], "review_changed")
        self.assertEqual(reviewed[2], old_original)
        self.assertIsNone(reviewed[4])
        self.assert_blank_result(reviewed)

    def test_scenario_change_blanks_result_but_keeps_exact_review_confirmation(self):
        state = self.applied()
        output = self.actions.scenario_changed(state)
        self.assertEqual(output[0]["review_digest"], state["review_digest"])
        self.assertEqual(output[4], state["reviewed_event"])
        self.assert_blank_result(output, disabled=False)
        # The callback must not mutate the original state object retained by Gradio.
        self.assertIsNotNone(state["result"])

    def test_server_blocks_stale_source_or_review_even_if_frontend_invalidation_is_skipped(self):
        state = self.applied()
        source_changed = form_values(state)
        source_changed[2] += " changed without input callback"
        edits_changed = form_values(state, edits={"location": "Changed location"})
        with patch.object(self.service, "_plan", side_effect=AssertionError("Stale confirmation cannot plan")) as planner:
            for arguments in (source_changed, edits_changed):
                with self.subTest(arguments=arguments[:2]):
                    output = self.actions.apply(state, *arguments, 3000, 1)
                    self.assertEqual(output[0]["status"], "apply_blocked")
                    self.assert_blank_result(output)
        planner.assert_not_called()

    def test_nullable_input_unknown_selection_and_stale_source_never_leave_old_displays(self):
        state = self.applied()
        with patch.object(self.service, "_plan", side_effect=AssertionError("Invalid input cannot plan")) as planner:
            # Nullable Textbox/API values must produce a safe blocked response,
            # rather than raising before the previous extraction/table clears.
            empty = self.actions.confirm(state, *([None] * 10))
            self.assertEqual(empty[0]["status"], "review_failed")
            self.assertIsNone(empty[2])
            self.assertFalse(empty[3])
            self.assert_blank_result(empty)
            # Unknown dropdown values must reset document fields as well as all
            # extraction, confirmation and plan outputs.
            selected = self.actions.select("__UNKNOWN_SYNTHETIC_CHOICE__")
            self.assertEqual(selected[:3], ("", "", ""))
            cleared = selected[3:]
            self.assertIsNone(cleared[2])
            self.assertFalse(cleared[3])
            self.assertIsNone(cleared[4])
            self.assert_blank_result(cleared)
            self.assertTrue(all(not value for value in cleared[9:]))
            # A skipped browser input event is still caught on Apply; stale
            # model JSON/provenance must disappear, not only its old plan.
            stale = form_values(state)
            stale[2] += " changed before Apply without an input callback"
            output = self.actions.apply(state, *stale, 3000, 1)
            self.assertEqual(output[0]["status"], "apply_blocked")
            self.assertIsNone(output[2])
            self.assertFalse(output[3])
            self.assert_blank_result(output)
        planner.assert_not_called()

    def test_explicit_live_failure_redacts_error_and_clears_saved_output_without_fallback(self):
        state = self.applied()
        document = state["document"]
        with patch("bluebikes.app_service._project_env", return_value={"OPENAI_API_KEY": "SYNTHETIC_TEST_TOKEN"}), \
                patch("bluebikes.app_service.extract_event", side_effect=RuntimeError("unsafe provider body SYNTHETIC_TEST_TOKEN")) as provider, \
                patch.object(self.service, "load_saved", side_effect=AssertionError("No automatic fallback")):
            output = self.actions.live(state, document["source_title"], document["source_url"], document["source_text"])
        provider.assert_called_once()
        self.assertEqual(len(output), 16)
        self.assertEqual(output[0]["status"], "live_failed")
        self.assertIsNone(output[2])
        self.assertFalse(output[3])
        self.assert_blank_result(output)
        self.assertNotIn("SYNTHETIC_TEST_TOKEN", str(output))
        self.assertNotIn("unsafe provider body", str(output))

    def test_live_missing_key_does_not_reuse_previous_saved_record(self):
        document = self.state["document"]
        with patch("bluebikes.app_service._project_env", return_value={}), \
                patch("bluebikes.app_service.extract_event", side_effect=AssertionError("No credential means no request")) as provider:
            output = self.actions.live(self.state, document["source_title"], document["source_url"], document["source_text"])
        provider.assert_not_called()
        self.assertEqual(output[0]["status"], "live_failed")
        self.assertIsNone(output[2])
        self.assert_blank_result(output)


class LocalLaunchTests(unittest.TestCase):
    def test_launch_binds_only_loopback_with_no_public_share_or_browser(self):
        app = Mock()
        with patch("bluebikes.app.create_app", return_value=app):
            result = launch_local(ROOT, port=7862, inline=True, prevent_thread_lock=True)
        self.assertIs(result, app)
        kwargs = app.launch.call_args.kwargs
        self.assertEqual(kwargs["server_name"], "127.0.0.1")
        self.assertEqual(kwargs["server_port"], 7862)
        self.assertFalse(kwargs["share"])
        self.assertFalse(kwargs["inbrowser"])
        self.assertFalse(kwargs["show_error"])
        self.assertFalse(kwargs["enable_monitoring"])

    def test_bad_port_is_rejected_before_screen_construction(self):
        with patch("bluebikes.app.create_app") as factory:
            for port in [True, "7860", 1023, 65536, -1, 7860.0]:
                with self.subTest(port=port), self.assertRaises(ValueError):
                    launch_local(ROOT, port=port)
        factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
