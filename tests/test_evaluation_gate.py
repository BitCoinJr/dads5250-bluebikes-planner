"""Evaluation-only identities survive edited facts/source and server-state tampering."""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

from bluebikes.app import _legacy_outputs
from bluebikes.app_service import AppService, EDIT_FIELDS
from bluebikes.presentation import executive_summary

ROOT = Path(__file__).resolve().parents[1]


def fields(state):
    return {k: deepcopy(state["original_llm"][k]) for k in EDIT_FIELDS}


class EvaluationGateTests(unittest.TestCase):
    def setUp(self):
        self.service = AppService(ROOT)

    def supplemental(self):
        return [id for label, id in self.service.choices() if label.startswith("[supplemental]")]

    def confirm_and_block(self, state):
        edits = {**fields(state), "city": "Boston", "start_date": "2026-04-21",
                 "end_date": "2026-04-21", "expected_crowd_size": 30000,
                 "ambiguities": ["Manual text cannot change evaluation scope."]}
        notes = "SYNTHETIC regression: edit all planning fields; not a human adjudication."
        confirmed = self.service.confirm(state, state["document"], edits, notes)
        self.assertEqual(confirmed["status"], "review_confirmed", confirmed.get("error"))
        outputs = _legacy_outputs(confirmed)
        self.assertFalse(outputs[5]["interactive"])
        self.assertIn("Evaluation only — excluded from staffing plans", outputs[1])
        # Neither editable facts nor the UI convenience flag grants authorization.
        confirmed["evaluation_only"] = False
        with patch.object(self.service, "_plan") as planner:
            blocked = self.service.apply(confirmed, state["document"], edits, notes)
            planner.assert_not_called()
        self.assertEqual(blocked["status"], "apply_blocked")
        self.assertIn("Evaluation only — excluded from staffing plans", blocked["error"])
        self.assertIsNone(blocked["result"])

    def test_all_three_remain_viewable_confirmable_but_not_plannable(self):
        self.assertEqual(len(self.supplemental()), 3)
        for source_id in self.supplemental():
            with self.subTest(source_id=source_id):
                state = self.service.select(source_id)
                self.assertTrue(state["evaluation_only"])
                self.confirm_and_block(state)

    def test_changed_source_and_mocked_live_response_preserve_original_identity(self):
        for source_id in self.supplemental():
            with self.subTest(source_id=source_id):
                state = self.service.select(source_id)
                doc = {**state["document"], "id": "renamed", "source_title": "Edited explanation",
                       "source_text": state["document"]["source_text"] + " Manual extra text."}
                invalid = self.service.invalidate(state, doc)
                self.assertTrue(invalid["evaluation_only"])
                record = deepcopy(state["original_llm"])
                metadata = {**state["provenance"], "source_id": "renamed", "mode": "live"}
                with patch("bluebikes.app_service._project_env", return_value={"OPENAI_API_KEY": "synthetic"}), \
                     patch("bluebikes.app_service.extract_event", return_value=(record, metadata)):
                    live = self.service.extract_live(invalid, doc)
                self.assertEqual(live["status"], "live_ready", live.get("error"))
                self.confirm_and_block(live)

    def test_saved_matching_supplemental_cannot_be_laundered_with_an_original_id(self):
        original = self.service.select("boston_marathon_2026")
        for source_id in self.supplemental():
            doc = {**self.service.select(source_id)["document"], "id": "boston_marathon_2026"}
            saved = self.service.load_saved(original, doc)
            self.assertEqual(saved["status"], "saved_ready")
            self.confirm_and_block(saved)
            invalid = self.service.invalidate(saved, {**doc, "source_text": doc["source_text"] + " edit"})
            self.assertTrue(invalid["evaluation_only"])
            self.assertEqual(invalid["source_origin"]["source_id"], source_id)

    def test_origin_cannot_be_replaced_or_removed(self):
        for mutation in ["replace", "remove"]:
            state = self.service.select(self.supplemental()[0])
            if mutation == "replace":
                state["source_origin"] = {"source_id": "boston_marathon_2026", "batch": "original"}
            else:
                del state["source_origin"]
            confirmed = self.service.confirm(state, state["document"], fields(state), "")
            self.assertEqual(confirmed["status"], "review_failed")
            self.assertIsNone(confirmed["review_digest"])

    def test_summary_uses_saved_result_values_and_is_independent_of_selection(self):
        chain = pd.read_csv(ROOT / "results/focused_event_chain.csv")
        html = executive_summary(chain)
        for text in ["12 → 13", "$72,000 → $78,000", "March 2026", "+3,000",
                     "independent of your event selection", "not actual Bluebikes",
                     "nine others share a pool", "uncalibrated retrospective"]:
            self.assertIn(text, html)
        changed = chain.copy()
        target = changed.event_increment_handling_actions.gt(0)
        changed.loc[target, "full_time_scenario"] = 14
        changed.loc[target, "crew_cost_scenario"] = 84000
        html = executive_summary(changed)
        self.assertIn("12 → 14", html)
        self.assertIn("$72,000 → $84,000", html)
        self.assertNotIn("$78,000", html)

if __name__ == "__main__":
    unittest.main()
