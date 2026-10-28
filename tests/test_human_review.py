"""Evidence-bound human annotations and regeneration: no real API calls."""
import copy
import csv
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from bluebikes.human_review import load_reviews, matching_review, review_html, sync_review_csvs, METHOD, DISPLAY_METHOD
from bluebikes.review_tables import write_review_csv
from bluebikes.event_validation import _export_review, evaluate_additional
from bluebikes.app import _extraction_cards
from bluebikes.app_service import AppService

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "docs/human_review_decisions.json", "fixtures/event_documents.json",
    "fixtures/event_documents_additional.json", "results/event_extraction_live.json",
    "results/event_extraction_additional_live.json", "prompts/event_extraction_v1.txt",
    "prompts/event_schema.json", "results/event_original_four_human_review.csv",
    "results/event_extraction_additional_review.csv", "docs/human_review_additional.md",
]


class HumanReviewTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / "build/human-review-tests"
        parent.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="case_", dir=parent))
        self.parent = parent
        for name in FILES:
            dest = self.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)

    def tearDown(self):
        if not self.root.resolve().is_relative_to(self.parent.resolve()):
            raise AssertionError("Cleanup target outside task test directory")
        shutil.rmtree(self.root)

    def read_rows(self, path):
        with (self.root / path).open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def test_seven_output_hashes_and_eight_topics_match_real_evidence(self):
        review = load_reviews(self.root)
        self.assertEqual(len(review["events"]), 7)
        self.assertEqual(len(review["assumptions"]), 8)
        self.assertEqual(review["record"]["record_compiled_date_jst"], "2026-10-27")

    def test_tampered_hash_unknown_id_and_changed_input_reject_annotations(self):
        path = self.root / "docs/human_review_decisions.json"
        original = path.read_text(encoding="utf-8")
        for key, value in [("output_sha256", "0"*64), ("source_id", "unknown_case")]:
            record = json.loads(original)
            record["original_event_reviews"][0][key] = value
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_reviews(self.root)
        path.write_text(original, encoding="utf-8")
        fixtures = self.root / "fixtures/event_documents.json"
        docs = json.loads(fixtures.read_text(encoding="utf-8"))
        docs[0]["source_text"] += " synthetic changed text"
        fixtures.write_text(json.dumps(docs), encoding="utf-8")
        with self.assertRaises(ValueError):
            load_reviews(self.root)

    def test_ui_annotations_do_not_mutate_raw_output_or_confirm_planning(self):
        service = AppService(ROOT)
        for source_id in load_reviews(ROOT)["events"]:
            state = service.select(source_id)
            original = copy.deepcopy(state["original_llm"])
            html = _extraction_cards(state, ROOT)
            self.assertIn("Human adjudication", html)
            self.assertIn(DISPLAY_METHOD, html)
            self.assertIn("Raw API output is unchanged", html)
            self.assertEqual(state["original_llm"], original)
            self.assertIsNone(state["reviewed_event"])
            self.assertIsNone(state["result"])
        hocr = _extraction_cards(service.select("additional_hocr_bu_2026"), ROOT)
        self.assertIn("strict lower-bound", hocr)
        self.assertIn("unsupported", hocr)
        bad = _extraction_cards(service.select("additional_baa_participants_only_2026"), ROOT)
        self.assertIn("FAIL_SEMANTIC_GROUNDING", bad)
        self.assertIn("unknown/null", bad)
        self.assertIn("2026-04-21", bad)  # original error is still visible
        self.assertIn("30,000", bad)

    def test_changed_session_input_or_output_has_no_inherited_adjudication(self):
        review = load_reviews(self.root)
        entry = next(iter(review["events"].values()))
        for field in ["id", "source_title", "source_url", "source_text"]:
            doc = copy.deepcopy(entry["document"])
            doc[field] += " changed"
            self.assertIsNone(matching_review(doc, entry["output"], self.root))
        output = copy.deepcopy(entry["output"]); output["city"] = "Other"
        self.assertEqual(review_html(entry["document"], output, self.root), "")

    def test_original_and_additional_exporters_preserve_all_review_fields(self):
        sync_review_csvs(self.root)
        original_path = "results/event_original_four_human_review.csv"
        extra_path = "results/event_extraction_additional_review.csv"
        before = {p: self.read_rows(p) for p in [original_path, extra_path]}
        incoming = []
        for row in before[original_path]:
            incoming.append({k: row[k] for k in ["evaluation_batch", "source_id", "source_url", "input_excerpt",
                                               "field", "provisional_reference", "actual_llm_output", "automatic_exact_match"]})
        result = write_review_csv(self.root / original_path, incoming)
        self.assertEqual(result["preserved_review_rows"], 20)
        docs = json.loads((self.root / "fixtures/event_documents_additional.json").read_text(encoding="utf-8"))
        saved = json.loads((self.root / "results/event_extraction_additional_live.json").read_text(encoding="utf-8"))
        saved["evaluation"] = evaluate_additional(saved["events"], docs)
        _export_review(self.root, docs, saved)
        for path, rows in before.items():
            after = self.read_rows(path)
            for a,b in zip(rows,after):
                for key,value in a.items():
                    self.assertEqual(value,b[key],(path,key))
                self.assertEqual(b["human_review_status"],"ADJUDICATED")
                self.assertEqual(b["adjudicated_at"],"")
        again = {p:self.read_rows(p) for p in before}
        write_review_csv(self.root / original_path, incoming)
        _export_review(self.root, docs, saved)
        self.assertEqual(again,{p:self.read_rows(p) for p in before})

    def test_reviewed_supplemental_input_change_fails_without_overwriting(self):
        path = self.root / "results/event_extraction_additional_review.csv"
        before = path.read_bytes()
        docs = json.loads((self.root / "fixtures/event_documents_additional.json").read_text(encoding="utf-8"))
        saved = json.loads((self.root / "results/event_extraction_additional_live.json").read_text(encoding="utf-8"))
        saved["evaluation"] = evaluate_additional(saved["events"], docs)
        docs[0]["source_text"] += " synthetic changed evidence"
        with self.assertRaisesRegex(ValueError,"human review work"):
            _export_review(self.root, docs, saved)
        self.assertEqual(path.read_bytes(),before)

    def test_sync_is_idempotent_and_keeps_unknown_times_blank(self):
        sync_review_csvs(self.root)
        files = ["results/event_original_four_human_review.csv","results/event_extraction_additional_review.csv"]
        before = {p:(self.root/p).read_bytes() for p in files}
        sync_review_csvs(self.root)
        self.assertEqual(before,{p:(self.root/p).read_bytes() for p in files})
        for p in files:
            for row in self.read_rows(p):
                self.assertEqual(row["adjudicated_at"],"")
                self.assertEqual(row["review_method"],METHOD)

if __name__ == "__main__":
    unittest.main()
