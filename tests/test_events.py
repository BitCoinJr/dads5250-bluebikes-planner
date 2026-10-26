"""Agent-authored contract and arithmetic tests; no live LLM claims or calls."""
import copy
import json
import os
from pathlib import Path
import shutil
import unittest
import uuid
from contextlib import contextmanager
from unittest.mock import patch

import pandas as pd
from jsonschema.exceptions import ValidationError

from bluebikes.events import (OPENAI_URL, PROJECT_ROOT, _hash, check_config,
                             evaluate_extractions, event_adjustments,
                             extract_event, extraction_payload, load_documents,
                             load_fixture_events, run_extraction, validate_event)


class FakeResponse:
    status_code = 200

    def __init__(self, record, status="completed", refusal=False):
        self.record = record
        self.status = status
        self.refusal = refusal

    def json(self):
        content = {"type": "refusal", "refusal": "mock refusal"} if self.refusal else {
            "type": "output_text", "text": json.dumps(self.record)}
        return {"id": "resp_mock_only", "model": "mock-only", "status": self.status,
                "output": [{"type": "message", "content": [content]}],
                "usage": {"total_tokens": 0}}


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


@contextmanager
def test_project(parent):
    # Python 3.13's Windows TemporaryDirectory uses a restrictive 0700 ACL that
    # can exclude the managed execution identity. Ordinary workspace dirs work.
    root = parent / ("case_" + uuid.uuid4().hex)
    root.mkdir()
    if not root.resolve().is_relative_to(parent.resolve()):
        raise AssertionError("Temporary test project escaped its workspace")
    try:
        yield root
    finally:
        if not root.resolve().is_relative_to(parent.resolve()):
            raise AssertionError("Refusing cleanup outside the test workspace")
        shutil.rmtree(root)


class EventTests(unittest.TestCase):
    def setUp(self):
        self.documents = load_documents()
        self.events = load_fixture_events()
        self.temp_parent = PROJECT_ROOT / "build/event-tests"
        self.temp_parent.mkdir(parents=True, exist_ok=True)

    def test_fixture_explicitly_not_llm_accuracy(self):
        result = run_extraction("fixture")
        self.assertEqual(result["api_calls"], 0)
        self.assertEqual(result["fixture_schema_valid_count"], 4)
        self.assertIsNone(result["evaluation"]["accuracy"])
        self.assertFalse(result["live_llm_verified"])

    def test_missing_key_does_not_fallback_to_fixtures(self):
        with patch("bluebikes.events._configuration", return_value={"api_key": None, "model": "gpt-4.1-mini", "key_source": "none"}):
            result = run_extraction("live")
        self.assertEqual(result["status"], "blocked_missing_api_key")
        self.assertEqual(result["events"], [])

    def test_schema_rejects_hallucinated_extra_key_and_bad_date(self):
        bad = copy.deepcopy(self.events[0])
        bad["confidence"] = 1.0
        with self.assertRaises(ValidationError):
            validate_event(bad)
        del bad["confidence"]
        bad["start_date"] = "2026-02-30"
        with self.assertRaises(ValidationError):
            validate_event(bad)

    def test_crowd_null_and_city_ambiguity(self):
        self.assertTrue(all(e["expected_crowd_size"] is None for e in self.events))
        self.assertIn("30,000 athletes", self.events[0]["evidence_text"])
        self.assertIsNone(self.events[3]["city"])

    def test_provenance_and_evidence_rejected(self):
        bad = copy.deepcopy(self.events[0])
        bad["source_url"] = "https://example.org/made-up"
        with self.assertRaises(ValueError):
            validate_event(bad, self.documents[0])
        bad = copy.deepcopy(self.events[0])
        bad["evidence_text"] = "unseen quote"
        with self.assertRaises(ValueError):
            validate_event(bad, self.documents[0])

    def test_unquoted_crowd_number_rejected(self):
        bad = copy.deepcopy(self.events[0])
        bad["expected_crowd_size"] = 500000
        with self.assertRaises(ValueError):
            validate_event(bad, self.documents[0])

    def test_request_contains_json_prompt_and_schema(self):
        payload = extraction_payload(self.documents[0])
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")
        self.assertTrue(payload["text"]["format"]["strict"])
        self.assertFalse(payload["store"])
        self.assertIn("JSON", payload["input"][0]["content"])
        self.assertIn("source_text", json.loads(payload["input"][1]["content"]))
        self.assertIn("schema", payload["text"]["format"])
        self.assertNotIn('"format": "uri"', json.dumps(payload["text"]["format"]["schema"]))
        self.assertNotIn("human_gold", json.dumps(payload))
        self.assertNotIn("Authorization", json.dumps(payload))

    def test_api_contract_with_mock_only(self):
        session = FakeSession(FakeResponse(self.events[0]))
        event, metadata = extract_event(self.documents[0], api_key="test-placeholder", session=session)
        self.assertEqual(event["city"], "Boston")
        self.assertEqual(session.calls[0][0], OPENAI_URL)
        self.assertFalse(session.calls[0][1]["allow_redirects"])
        self.assertEqual(metadata["model"], "mock-only")
        self.assertNotIn("test-placeholder", json.dumps(metadata))

    def test_incomplete_api_response_rejected(self):
        session = FakeSession(FakeResponse(self.events[0], "incomplete"))
        with self.assertRaises(ValueError):
            extract_event(self.documents[0], api_key="test-placeholder", session=session)

    def test_refused_api_response_rejected(self):
        session = FakeSession(FakeResponse(self.events[0], refusal=True))
        with self.assertRaisesRegex(ValueError, "refused"):
            extract_event(self.documents[0], api_key="test-placeholder", session=session)

    def test_non200_response_no_body_or_key_disclosure(self):
        response = FakeResponse(self.events[0])
        response.status_code = 401
        with self.assertRaisesRegex(RuntimeError, "HTTP 401"):
            extract_event(self.documents[0], api_key="test-placeholder", session=FakeSession(response))

    def test_manual_adjustment_arithmetic_and_no_double_entry(self):
        forecast = pd.DataFrame({"year": [2026] * 3, "month": [4, 7, 10],
                                "city": ["Boston", "Boston", "Cambridge"],
                                "demand_bikes": [100, 200, 300]})
        zero = event_adjustments(forecast, self.events)
        self.assertEqual(zero.demand_bikes.tolist(), [100, 200, 300])
        scenario = event_adjustments(forecast, self.events + [self.events[0]], 60)
        self.assertEqual(scenario.demand_bikes.tolist(), [160, 260, 360])
        self.assertEqual(scenario.event_count.tolist(), [1, 1, 1])
        self.assertEqual(forecast.demand_bikes.tolist(), [100, 200, 300])

    def test_multimonth_increment_prorated_not_duplicated(self):
        event = copy.deepcopy(self.events[0])
        event["start_date"], event["end_date"] = "2026-04-30", "2026-05-02"
        forecast = pd.DataFrame({"year": [2026, 2026], "month": [4, 5], "city": ["Boston"] * 2,
                                "demand_bikes": [0, 0]})
        scenario = event_adjustments(forecast, [event], 90)
        self.assertEqual(scenario.event_increment_bikes.tolist(), [30, 60])

    def test_invalid_coefficient_and_duplicate_month_rejected(self):
        forecast = pd.DataFrame({"year": [2026], "month": [4], "city": ["Boston"], "demand_bikes": [0]})
        for coefficient in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                event_adjustments(forecast, self.events, coefficient)
        with self.assertRaises(ValueError):
            event_adjustments(pd.concat([forecast, forecast]), self.events)

    def test_evaluator_detects_field_error_against_agent_draft_key(self):
        predictions = copy.deepcopy(self.events)
        predictions[0]["city"] = None
        score = evaluate_extractions(predictions, self.documents)
        self.assertEqual(score["correct_fields"], 19)
        self.assertEqual(score["total_fields"], 20)
        self.assertEqual(score["accuracy"], .95)
        self.assertEqual(score["reference_status"], "provisional_agent_draft_labels_human_review_pending")

    def test_safe_config_never_exposes_key(self):
        with patch("bluebikes.events._configuration", return_value={
                "api_key": "UNIT_TEST_SECRET", "key_source": "project_dotenv", "model": "gpt-4.1-mini"}):
            result = check_config()
        self.assertTrue(result["key_present"])
        self.assertEqual(result["key_source"], "project_dotenv")
        self.assertNotIn("UNIT_TEST_SECRET", json.dumps(result))

    def test_dotenv_whitelist_and_environment_precedence(self):
        with test_project(self.temp_parent) as root:
            self.assertTrue(root.resolve().is_relative_to(self.temp_parent.resolve()))
            (root / ".env").write_text('OPENAI_API_KEY="UNIT_TEST_SECRET"\nOPENAI_MODEL=gpt-4.1-mini\nUNRELATED=ignored\n', encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True), patch("bluebikes.events._windows_user_env", return_value={}):
                self.assertEqual(check_config(root)["key_source"], "project_dotenv")
            with patch.dict(os.environ, {"OPENAI_API_KEY": "PROCESS_TEST_SECRET"}, clear=True):
                result = check_config(root)
                self.assertEqual(result["key_source"], "process_environment")
                self.assertNotIn("PROCESS_TEST_SECRET", json.dumps(result))

    def _write_mock_recording(self, root):
        """Create an entirely mocked artifact in a temporary test directory."""
        for folder in ("prompts", "fixtures"):
            shutil.copytree(PROJECT_ROOT / folder, root / folder)
        calls = []
        for document, event in zip(self.documents, self.events):
            calls.append({"source_id": document["id"], "provider": "openai", "mode": "live",
                          "endpoint": OPENAI_URL, "response_status": "completed", "response_id": "resp_mock_only",
                          "requested_model": "gpt-4.1-mini", "model": "mock-only",
                          "request_sha256": _hash(extraction_payload(document, "gpt-4.1-mini", root)),
                          "output_sha256": _hash(event)})
        artifact = {"status": "completed", "mode": "live", "provider": "openai", "live_llm_verified": True,
                    "events": self.events, "calls": calls, "api_calls": 4}
        (root / "results").mkdir()
        path = root / "results/event_extraction_live.json"
        path.write_text(json.dumps(artifact), encoding="utf-8")
        return path

    def test_recorded_mode_no_network_and_missing_artifact_blocked(self):
        with test_project(self.temp_parent) as root:
            self.assertTrue(root.resolve().is_relative_to(self.temp_parent.resolve()))
            self._write_mock_recording(root)
            with patch("requests.Session.post", side_effect=AssertionError("No network in recorded mode")):
                result = run_extraction("recorded", root)
            self.assertEqual(result["api_calls"], 0)
            self.assertEqual(result["recorded_api_calls"], 4)
            self.assertEqual(result["status"], "recorded_live_outputs_validated")
            (root / "results/event_extraction_live.json").unlink()
            self.assertEqual(run_extraction("recorded", root)["status"], "blocked_missing_recorded_outputs")

    def test_recorded_mode_rejects_stale_prompt_and_modified_output(self):
        with test_project(self.temp_parent) as root:
            self.assertTrue(root.resolve().is_relative_to(self.temp_parent.resolve()))
            path = self._write_mock_recording(root)
            artifact = json.loads(path.read_text(encoding="utf-8"))
            artifact["events"][0]["city"] = None
            path.write_text(json.dumps(artifact), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "provenance/hash mismatch"):
                run_extraction("recorded", root)
            artifact["events"][0]["city"] = "Boston"
            path.write_text(json.dumps(artifact), encoding="utf-8")
            with (root / "prompts/event_extraction_v1.txt").open("a", encoding="utf-8") as handle:
                handle.write("\nChanged prompt in synthetic test.\n")
            with self.assertRaisesRegex(ValueError, "provenance/hash mismatch"):
                run_extraction("recorded", root)


if __name__ == "__main__":
    unittest.main()
