"""Synthetic supplemental contract tests. Network calls are mocked throughout."""
import copy
import csv
import json
from pathlib import Path
import shutil
import unittest
import uuid
from unittest.mock import patch

from bluebikes.events import OPENAI_URL, PROJECT_ROOT, _hash, extraction_payload
from bluebikes.event_validation import (
    DOCUMENTS, EVALUATION, FREEZE, LIVE, ORIGINALS, REVIEW_CSV,
    evaluate_additional, freeze_references, load_additional_documents,
    run_additional_evaluation,
)


class AdditionalEventTests(unittest.TestCase):
    def setUp(self):
        parent = PROJECT_ROOT / "build/additional-event-tests"
        parent.mkdir(parents=True, exist_ok=True)
        self.root = parent / ("case_" + uuid.uuid4().hex)
        self.root.mkdir()
        self.assertTrue(self.root.resolve().is_relative_to(parent.resolve()))
        self.parent = parent
        for name in ORIGINALS + [DOCUMENTS]:
            destination = self.root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(PROJECT_ROOT / name, destination)
        self.docs = load_additional_documents(self.root)
        self.settings = {"api_key": "MOCK_CREDENTIAL_NOT_REAL", "model": "gpt-4.1-mini", "key_source": "mock"}

    def tearDown(self):
        if not self.root.resolve().is_relative_to(self.parent.resolve()):
            raise AssertionError("Refusing test cleanup outside its workspace")
        shutil.rmtree(self.root)

    def _mock_extract(self, document, **kwargs):
        # Freezing must happen before even a mocked request is dispatched.
        self.assertTrue((self.root / FREEZE).is_file())
        record = copy.deepcopy(document["reference"])
        payload = extraction_payload(document, "gpt-4.1-mini", self.root)
        return record, {"source_id": document["id"], "provider": "openai", "mode": "live",
                        "endpoint": OPENAI_URL, "requested_model": "gpt-4.1-mini", "model": "mock-only",
                        "response_status": "completed", "response_id": "resp_mock_only",
                        "request_sha256": _hash(payload), "output_sha256": _hash(record),
                        "usage": {"input_tokens": 0, "output_tokens": 0}}

    def _mock_live(self):
        with patch("bluebikes.event_validation._configuration", return_value=self.settings), \
                patch("bluebikes.event_validation.extract_event", side_effect=self._mock_extract):
            return run_additional_evaluation("live", self.root)

    def test_positive_and_participant_references_are_distinct_roles(self):
        self.assertEqual([doc["reference"]["expected_crowd_size"] for doc in self.docs], [300000, 325000, None])
        self.assertEqual([doc["crowd_reference"]["qualifier"] for doc in self.docs], ["more than", "approximately", None])
        self.assertEqual(len({doc["event_identity"] for doc in self.docs}), 2)
        self.assertTrue(all(len(doc["source_text"].replace("...", " ").split()) <= 25 for doc in self.docs))

    def test_crowd_confusion_is_detected_without_revising_references(self):
        records = [copy.deepcopy(doc["reference"]) for doc in self.docs]
        records[0]["expected_crowd_size"] = 12000
        evaluation = evaluate_additional(records, self.docs)
        self.assertEqual(evaluation["non_audience_substitutions"], 1)
        self.assertEqual(evaluation["positive_crowd_matches"], 1)
        self.assertEqual(evaluation["participant_only_null_matches"], 1)
        self.assertFalse(evaluation["human_review_complete"])
        self.assertIn("non_audience_number_used_as_crowd", [note["flag"] for note in evaluation["automated_quality_notes"]])

    def test_qualifier_omission_and_unsupported_dates_are_separate_automatic_flags(self):
        records = [copy.deepcopy(doc["reference"]) for doc in self.docs]
        records[0]["ambiguities"] = []
        records[2]["start_date"] = records[2]["end_date"] = "2026-04-21"
        evaluation = evaluate_additional(records, self.docs)
        notes = evaluation["automated_quality_notes"]
        self.assertEqual(sum(note["flag"] == "unsupported_date_inference" for note in notes), 2)
        self.assertTrue(any(note["flag"] == "crowd_qualifier_omitted_from_ambiguities" and note["source_id"] == self.docs[0]["id"] for note in notes))
        self.assertFalse(evaluation["automated_notes_are_human_judgments"])

    def test_mock_live_is_separate_and_original_baseline_is_unchanged(self):
        baseline = (self.root / "results/event_extraction_live.json").read_bytes()
        result = self._mock_live()
        self.assertEqual(result["api_attempts"], 3)
        self.assertEqual(result["api_calls"], 3)
        self.assertEqual((self.root / "results/event_extraction_live.json").read_bytes(), baseline)
        self.assertEqual(result["evaluation"]["total_fields"], 15)
        with (self.root / REVIEW_CSV).open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["human_judgment"] == "" and row["human_review_status"] == "PENDING" for row in rows))

    def test_recorded_rerun_makes_no_calls_and_preserves_review_entries(self):
        self._mock_live()
        path = self.root / REVIEW_CSV
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        rows[0]["human_review_notes"] = "SYNTHETIC TEST NOTE, NOT A HUMAN JUDGMENT"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        with patch("bluebikes.event_validation.extract_event", side_effect=AssertionError("No calls in replay")):
            result = run_additional_evaluation("recorded", self.root)
        self.assertEqual(result["api_calls"], 0)
        self.assertEqual(result["recorded_api_calls"], 3)
        self.assertIn("SYNTHETIC TEST NOTE", path.read_text(encoding="utf-8"))

    def test_changed_frozen_reference_or_original_prompt_is_rejected(self):
        self._mock_live()
        path = self.root / "prompts/event_extraction_v1.txt"
        path.write_text(path.read_text(encoding="utf-8") + "\nSYNTHETIC TEST CHANGE\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Frozen inputs changed"):
            run_additional_evaluation("recorded", self.root)

    def test_missing_key_and_missing_recording_never_use_fixtures(self):
        with patch("bluebikes.event_validation._configuration", return_value={"api_key": None}):
            result = run_additional_evaluation("live", self.root)
        self.assertEqual(result["api_attempts"], 0)
        self.assertEqual(result["events"], [])
        self.assertEqual(run_additional_evaluation("recorded", self.root)["status"], "blocked_missing_additional_live_outputs")

    def test_failed_request_is_recorded_without_exposing_credentials(self):
        with patch("bluebikes.event_validation._configuration", return_value=self.settings), \
                patch("bluebikes.event_validation.extract_event", side_effect=RuntimeError("unsafe error body")):
            with self.assertRaisesRegex(RuntimeError, "redacted attempt metadata"):
                run_additional_evaluation("live", self.root)
        saved = json.loads((self.root / LIVE).read_text(encoding="utf-8"))
        self.assertEqual(saved["api_attempts"], 1)
        self.assertEqual(saved["api_calls"], 0)
        self.assertEqual(saved["attempts"][0]["status"], "failed")
        self.assertNotIn("unsafe error body", json.dumps(saved))
        self.assertNotIn("MOCK_CREDENTIAL_NOT_REAL", json.dumps(saved))


if __name__ == "__main__":
    unittest.main()
