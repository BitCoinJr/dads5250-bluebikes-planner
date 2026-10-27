"""Service tests use saved real evidence and mocked HTTP, never live API calls."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from bluebikes.app_service import AppService, EDIT_FIELDS


ROOT = Path(__file__).resolve().parents[1]
MARATHON = "boston_marathon_2026"
HOCR = "head_of_charles_2026"


def edits(state):
    return {field: deepcopy(state["original_llm"][field]) for field in EDIT_FIELDS}


class AppServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = AppService(ROOT)
        self.state = self.service.select(MARATHON)
        self.doc = deepcopy(self.state["document"])
        self.fields = edits(self.state)

    def confirmed(self):
        return self.service.confirm(self.state, self.doc, self.fields, "")

    def test_all_seven_choices_load_saved_real_without_key_or_evaluation_writes(self):
        protected = [
            "results/event_extraction_live.json", "results/event_extraction_additional_live.json",
            "results/event_extraction_additional_freeze.json",
            "results/event_original_four_human_review.csv",
            "results/event_extraction_additional_review.csv",
            "results/event_extraction_evaluation.json",
            "results/event_extraction_additional_evaluation.json",
            "fixtures/event_documents.json", "fixtures/event_documents_additional.json",
        ]
        before = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in protected}
        with patch("bluebikes.app_service._project_env", side_effect=AssertionError("No key access for saved replay")), \
             patch("bluebikes.app_service.extract_event", side_effect=AssertionError("No API call")):
            self.assertEqual(len(self.service.choices()), 7)
            for _, choice in self.service.choices():
                state = self.service.select(choice)
                self.assertEqual(state["status"], "saved_ready", state.get("error"))
                self.assertEqual(state["provenance"]["mode"], "recorded")
                self.assertIsNone(state["review_digest"])
            state = self.confirmed()
            result = self.service.apply(state, self.doc, self.fields, "")
            self.assertEqual(result["status"], "plan_ready", result.get("error"))
        after = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in protected}
        self.assertEqual(before, after)

    def test_apply_requires_confirmation_and_checks_stale_fields_notes_and_source(self):
        result = self.service.apply(self.state, self.doc, self.fields, "")
        self.assertEqual(result["status"], "apply_blocked")
        self.assertIsNone(result["result"])
        confirmed = self.confirmed()
        self.assertEqual(confirmed["status"], "review_confirmed")
        for changed_doc, changed_edits, changed_notes in [
            ({**self.doc, "source_text": self.doc["source_text"] + " edited"}, self.fields, ""),
            (self.doc, {**self.fields, "location": "new manual location"}, "correction"),
            (self.doc, self.fields, "changed notes"),
        ]:
            result = self.service.apply(confirmed, changed_doc, changed_edits, changed_notes)
            self.assertEqual(result["status"], "apply_blocked")
            self.assertIsNone(result["review_digest"])
            self.assertIsNone(result["result"])

    def test_forged_review_or_extraction_state_is_rejected(self):
        confirmed = self.confirmed()
        forged = deepcopy(confirmed)
        forged["original_llm"]["city"] = "Cambridge"
        forged_fields = {**self.fields, "city": "Cambridge"}
        self.assertEqual(self.service.confirm(forged, self.doc, forged_fields, "changed")["status"], "review_failed")
        forged = deepcopy(confirmed)
        forged["reviewed_event"]["city"] = "Cambridge"
        forged["review_digest"] = "0" * 64
        self.assertEqual(self.service.apply(forged, self.doc, forged_fields, "changed")["status"], "apply_blocked")
        other_server = AppService(ROOT)
        self.assertEqual(other_server.apply(confirmed, self.doc, self.fields, "")["status"], "apply_blocked")

    def test_input_or_review_invalidation_has_correct_scope(self):
        confirmed = self.confirmed()
        unconfirmed = self.service.invalidate_review(confirmed)
        self.assertEqual(unconfirmed["original_llm"], confirmed["original_llm"])
        self.assertIsNone(unconfirmed["review_digest"])
        self.assertIsNone(unconfirmed["result"])
        changed_doc = {**self.doc, "source_title": self.doc["source_title"] + " changed"}
        invalid = self.service.invalidate(confirmed, changed_doc)
        self.assertIsNone(invalid["original_llm"])
        self.assertIsNone(invalid["reviewed_event"])
        self.assertIsNone(invalid["result"])
        saved = self.service.load_saved(confirmed, changed_doc)
        self.assertEqual(saved["status"], "saved_failed")
        self.assertIsNone(saved["original_llm"])
        self.assertIsNone(saved["result"])

    def test_live_failure_redacts_exception_and_clears_previous_outputs(self):
        secret_marker = "sk-private-unit-test-not-a-real-key"
        confirmed = self.confirmed()
        with patch("bluebikes.app_service._project_env", return_value={"OPENAI_API_KEY": secret_marker}), \
             patch("bluebikes.app_service.extract_event", side_effect=RuntimeError("Bearer " + secret_marker)):
            failed = self.service.extract_live(confirmed, self.doc)
        self.assertEqual(failed["status"], "live_failed")
        self.assertNotIn(secret_marker, json.dumps(failed))
        for field in ["original_llm", "reviewed_event", "review_digest", "result"]:
            self.assertIsNone(failed[field])
        loaded = self.service.load_saved(failed, self.doc)
        self.assertEqual(loaded["status"], "saved_ready")  # Explicit separate action.

    def test_missing_project_key_never_falls_back_to_process_credentials(self):
        with patch("bluebikes.app_service._project_env", return_value={}), \
             patch("bluebikes.app_service.extract_event") as live:
            failed = self.service.extract_live(self.state, self.doc)
            live.assert_not_called()
        self.assertEqual(failed["status"], "live_failed")
        self.assertIn("Project .env", failed["error"])

    def test_explicit_live_calls_existing_adapter_once_without_persistence(self):
        record = deepcopy(self.state["original_llm"])
        metadata = {**self.state["provenance"], "mode": "live"}
        with patch("bluebikes.app_service._project_env", return_value={
                "OPENAI_API_KEY": "fake-test-value", "OPENAI_MODEL": "gpt-4.1-mini"}), \
             patch("bluebikes.app_service.extract_event", return_value=(record, metadata)) as live:
            result = self.service.extract_live(self.state, self.doc)
        self.assertEqual(result["status"], "live_ready")
        live.assert_called_once()
        self.assertEqual(live.call_args.kwargs["api_key"], "fake-test-value")
        self.assertEqual(live.call_args.kwargs["model"], "gpt-4.1-mini")

    def test_nullable_unknowns_require_manual_notes_and_apply_guards(self):
        state = self.service.select(HOCR)
        doc = state["document"]
        fields = edits(state)
        self.assertIsNone(fields["city"])
        confirmed = self.service.confirm(state, doc, fields, "")
        blocked = self.service.apply(confirmed, doc, fields, "")
        self.assertEqual(blocked["status"], "apply_blocked")
        changed = {**fields, "city": "Boston"}
        self.assertEqual(self.service.confirm(state, doc, changed, "")["status"], "review_failed")
        reviewed = self.service.confirm(state, doc, changed, "Manual endpoint assignment; not in the supplied excerpt.")
        self.assertEqual(reviewed["status"], "review_confirmed")
        missing_dates = {**self.fields, "start_date": None, "end_date": None}
        reviewed = self.service.confirm(self.state, self.doc, missing_dates, "Dates intentionally unknown.")
        self.assertEqual(self.service.apply(reviewed, self.doc, missing_dates, "Dates intentionally unknown.")["status"], "apply_blocked")
        unknown_city = {**self.fields, "city": "Unknown municipality"}
        reviewed = self.service.confirm(self.state, self.doc, unknown_city, "Manual city entry.")
        self.assertEqual(self.service.apply(reviewed, self.doc, unknown_city, "Manual city entry.")["status"], "apply_blocked")

    def test_real_saved_chain_hire_lead_and_matched_cost_horizons(self):
        result = self.service.apply(self.confirmed(), self.doc, self.fields, "")
        self.assertEqual(result["status"], "plan_ready", result.get("error"))
        json.dumps(result, allow_nan=False)
        chain = {row["month"]: row for row in result["result"]["monthly_chain"]}
        april, march, january = chain[4], chain[3], chain[1]
        self.assertEqual(april["full_time_base"], 12)
        self.assertEqual(april["full_time_scenario"], 13)
        self.assertEqual(april["crew_cost_base"], 72000)
        self.assertEqual(april["crew_cost_scenario"], 78000)
        self.assertEqual(april["prior_month_hires_decision_base"], 3)
        self.assertEqual(april["prior_month_hires_decision_scenario"], 4)
        self.assertEqual(april["hire_decision_month_for_active_month"], "2026-03")
        self.assertEqual(march["current_decisions_effective_month"], "2026-04")
        self.assertEqual(april["prior_month_seasonal_start_decision_scenario"],
                         march["seasonal_start_decision_scenario"])
        self.assertEqual(january["hire_decision_month_for_active_month"], "No Dec2025 decision / fixed initial")
        self.assertEqual(april["full_time_scenario"],
                         march["full_time_scenario"] + march["hires_decision_scenario"] - march["fires_notice_scenario"])
        self.assertEqual(january["full_time_scenario"], january["full_time_base"])
        periods = {(r["scenario"], r["period_months"]): r for r in result["result"]["period_comparison"]}
        self.assertEqual(periods["initial_crews", 12]["crew_cash_cost_in_period"], 1008000)
        self.assertEqual(periods["initial_crews", 9]["crew_cash_cost_in_period"], 756000)
        self.assertEqual(periods["no_event", 9]["crew_cash_cost_in_period"], 1342800)
        self.assertIsNone(periods["no_event", 9]["mandatory_seasonal_tail_cost_2027_separate"])

    def test_conversion_keeps_120_and_penalty_per_handling_action(self):
        result = self.service.apply(self.confirmed(), self.doc, self.fields, "", conversion=2)
        self.assertEqual(result["status"], "plan_ready", result.get("error"))
        output = result["result"]
        self.assertEqual(output["summary"]["course_bikes_per_shift"], 120)
        self.assertEqual(output["summary"]["handling_actions_per_course_bike"], 2)
        for row in output["period_comparison"]:
            self.assertEqual(row["course_bikes_per_shift"], 120)
            self.assertEqual(row["assumed_users_per_uncovered_handling_action"], 1)
            self.assertAlmostEqual(row["assumed_service_loss_in_period"],
                                   row["uncovered_handling_actions"] * 5.70)
        april = next(row for row in output["monthly_chain"] if row["month"] == 4)
        self.assertAlmostEqual(april["demand_handling_actions_scenario"] - april["demand_handling_actions_base"], 3000)
        self.assertAlmostEqual(april["demand_bikes_change"], 1500)


if __name__ == "__main__":
    unittest.main()
