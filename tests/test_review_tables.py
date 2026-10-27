"""Hand-entered review work must survive regeneration or stop it safely."""
import copy
import csv
from pathlib import Path
import shutil
import unittest
import uuid

from bluebikes.review_tables import write_review_csv


def evidence(source="example", field="city"):
    return {"evaluation_batch": "original_four_frozen", "source_id": source, "source_url": "https://example.org/event",
            "input_excerpt": "Example excerpt", "field": field,
            "provisional_reference": '"Boston"', "actual_llm_output": '"Boston"',
            "automatic_exact_match": True,
            "human_judgment": "", "reviewer": "", "notes": "", "human_review_status": "PENDING"}


class ReviewTableTests(unittest.TestCase):
    def setUp(self):
        self.parent = Path(__file__).resolve().parents[1] / "build/review-table-tests"
        self.parent.mkdir(parents=True, exist_ok=True)
        self.root = self.parent / ("case_" + uuid.uuid4().hex)
        self.root.mkdir()
        self.path = self.root / "review.csv"
        self.row = evidence()
        write_review_csv(self.path, [self.row])

    def tearDown(self):
        if not self.root.resolve().is_relative_to(self.parent.resolve()):
            raise AssertionError("Refusing cleanup outside the test workspace")
        shutil.rmtree(self.root)

    def read(self):
        with self.path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def save(self, rows):
        with self.path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def add_human_work(self):
        rows = self.read()
        rows[0].update({"human_judgment": "REQUIRES DISCUSSION", "reviewer": "TEST REVIEWER",
                        "notes": "Synthetic test note, comma, and\nsecond line — 日本語", "human_review_status": "IN_PROGRESS",
                        "reviewed_at": "TEST-ONLY TIMESTAMP"})
        self.save(rows)
        return rows[0]

    def test_identical_evidence_preserves_all_human_fields_and_extra_column(self):
        old = self.add_human_work()
        result = write_review_csv(self.path, [self.row])
        new = self.read()[0]
        for column in ["human_judgment", "reviewer", "notes", "human_review_status", "reviewed_at"]:
            self.assertEqual(new[column], old[column])
        self.assertEqual(result["preserved_review_rows"], 1)

    def test_reviewed_evidence_changes_are_rejected_without_touching_file(self):
        self.add_human_work()
        before = self.path.read_bytes()
        for column in ["evaluation_batch", "source_url", "input_excerpt", "provisional_reference", "actual_llm_output", "automatic_exact_match"]:
            changed = copy.deepcopy(self.row)
            changed[column] = "CHANGED TEST EVIDENCE"
            with self.assertRaisesRegex(ValueError, "human review work"):
                write_review_csv(self.path, [changed])
            self.assertEqual(self.path.read_bytes(), before)

    def test_notes_alone_protect_row_even_when_status_is_pending(self):
        rows = self.read()
        rows[0]["notes"] = "UNFINISHED SYNTHETIC REVIEW NOTE"
        self.save(rows)
        changed = {**self.row, "actual_llm_output": '"Cambridge"'}
        with self.assertRaisesRegex(ValueError, "human review work"):
            write_review_csv(self.path, [changed])

    def test_removed_reviewed_row_is_rejected_but_empty_fixture_input_is_noop(self):
        self.add_human_work()
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "human review work"):
            write_review_csv(self.path, [evidence("different_event")])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertTrue(write_review_csv(self.path, [])["skipped_empty"])
        self.assertEqual(self.path.read_bytes(), before)

    def test_unreviewed_changes_and_new_rows_remain_pending(self):
        changed = {**self.row, "actual_llm_output": '"Cambridge"', "automatic_exact_match": False}
        write_review_csv(self.path, [changed, evidence("new_event")])
        rows = self.read()
        self.assertEqual(rows[0]["actual_llm_output"], '"Cambridge"')
        self.assertTrue(all(row["human_judgment"] == "" and row["human_review_status"] == "PENDING" for row in rows))

    def test_duplicate_identity_is_rejected_before_any_write(self):
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "Duplicate incoming"):
            write_review_csv(self.path, [self.row, self.row])
        self.assertEqual(self.path.read_bytes(), before)
        self.save([self.read()[0], self.read()[0]])
        duplicated = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "Duplicate existing"):
            write_review_csv(self.path, [self.row])
        self.assertEqual(self.path.read_bytes(), duplicated)


if __name__ == "__main__":
    unittest.main()
