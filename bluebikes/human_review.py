"""Hash-bound human adjudications, separate from immutable API/model evidence."""
from __future__ import annotations

import csv
from html import escape
import json
from pathlib import Path

from .events import _hash, extraction_payload

ROOT = Path(__file__).resolve().parents[1]
RECORD = "docs/human_review_decisions.json"
METHOD = "AI-assisted review, explicitly adjudicated by Satoshi in chat"
# METHOD is the provenance string stored in the review CSVs; keep it unchanged.
# DISPLAY_METHOD is the shorter wording shown to readers in the app and notebooks.
DISPLAY_METHOD = "AI-assisted review, confirmed by the reviewer"
REVIEWER = "Satoshi Nakamura"
TOPICS = (
    "crew_unit_review", "daily_inventory_reset_review", "hiring_and_contract_review",
    "shared_pool_review", "shortage_loss_conversion_review", "event_uplift_review",
    "forecast_backtest_review", "demand_and_ebike_sensitivity_review",
)


def load_reviews(root=None):
    """Verify source IDs, frozen request and output hashes before exposing judgments."""
    root = Path(root or ROOT)
    if not (root / RECORD).is_file():
        return {"record": None, "events": {}, "assumptions": {}}
    read = lambda path: json.loads((root / path).read_text(encoding="utf-8-sig"))
    record = read(RECORD)
    decisions = record["original_event_reviews"] + record["supplemental_hocr_reviews"] + record["reviews"]
    indexed = {d["source_id"]: d for d in decisions}
    if len(indexed) != len(decisions):
        raise ValueError("Duplicate human-review source ID")
    events = {}
    for inputs, outputs, batch in [
        ("fixtures/event_documents.json", "results/event_extraction_live.json", "original"),
        ("fixtures/event_documents_additional.json", "results/event_extraction_additional_live.json", "supplemental"),
    ]:
        docs, saved = read(inputs), read(outputs)
        if len(docs) != len(saved["events"]) or len(docs) != len(saved["calls"]):
            raise ValueError("Saved input/output/call alignment mismatch")
        for doc, output, call in zip(docs, saved["events"], saved["calls"]):
            source_id = doc["id"]
            if source_id not in indexed:
                continue
            decision = indexed[source_id]
            if (call["source_id"] != source_id
                    or decision["human_reviewer"] != REVIEWER
                    or decision["output_sha256"] != call["output_sha256"]
                    or decision["output_sha256"] != _hash(output)
                    or output["source_url"] != doc["source_url"]
                    or call["request_sha256"] != _hash(extraction_payload(doc, call["requested_model"], root))):
                raise ValueError("Human review does not match frozen input/output evidence: " + source_id)
            events[source_id] = {"decision": decision, "document": doc,
                                 "output": output, "batch": batch}
    if set(events) != set(indexed):
        raise ValueError("Human-review source ID missing from saved actual API records")
    assumptions = {key: record[key] for key in TOPICS}
    if any(v["human_reviewer"] != REVIEWER for v in assumptions.values()):
        raise ValueError("Unexpected assumption reviewer")
    return {"record": record, "events": events, "assumptions": assumptions}


def annotation_lines(entry, record):
    decision = entry["decision"]
    notes = list(decision.get("required_notes", []))
    for field, item in decision.get("fields", {}).items():
        if item.get("verdict") == "incorrect":
            notes.append(field + ": rejected; use unknown/null in a corrected record. " + item["reason"])
        elif field == "location":
            notes.append("Location is semantically acceptable; the preserved exact-string score is unchanged.")
    if "hocr" in decision["source_id"] or decision["source_id"] == "head_of_charles_2026":
        notes.append(record["confirmed_cross_source_rule"])
    notes.append("Raw API output is unchanged. This is adjudication and a separate annotation, not a corrected model response.")
    return notes


def matching_review(document, output, root=None):
    """No annotation is carried across edits or a different source/output."""
    review = load_reviews(root)
    entry = review["events"].get(document.get("id"))
    if entry is None or _hash(output) != entry["decision"]["output_sha256"]:
        return None
    if any(document.get(k) != entry["document"].get(k)
           for k in ("source_title", "source_url", "source_text")):
        return None
    return review, entry


def review_html(document, output, root=None):
    try:
        match = matching_review(document, output, root)
    except (OSError, ValueError, KeyError):
        return '<div class="bb-review-note">Human annotation unavailable: evidence mismatch or invalid review record. Do not infer review approval.</div>'
    if match is None:
        return ""
    review, entry = match
    decision = entry["decision"]
    notes = annotation_lines(entry, review["record"])
    return ('<div class="bb-review-note bb-human-adjudication"><strong>Human adjudication — separate annotation</strong>'
            '<p>' + escape(decision["human_judgment"]) + '</p><p>'
            + escape("Reviewer: " + REVIEWER + " (" + DISPLAY_METHOD + "), "
                     + review["record"]["record_compiled_date_jst"] + ".") + '</p>'
            + '<ul>' + ''.join('<li>' + escape(n) + '</li>' for n in notes) + '</ul>'
            + '<p>Saved-excerpt review only; not independent website verification. Session confirmation and Apply are still required.</p></div>')


def status_text(root=None):
    review = load_reviews(root)
    if not review["record"]:
        return "No integrated human decision record is available; human adjudication is pending."
    return (f"{len(review['events'])} event cases adjudicated by {REVIEWER}; "
            f"{len(review['assumptions'])} model topics conditionally accepted as disclosed assumptions. "
            "Three accepted original cases, three HOCR cases with separate annotations, one participant/date grounding failure. "
            "Raw outputs and frozen 19/20 and 11/15 scores are unchanged. "
            "Not an all-pass, empirical validation, TA approval or all-member review. "
            "Method: " + DISPLAY_METHOD + ". Reviewed 2026-10-27.")


def sync_review_csvs(root=None):
    """Apply only authorized review columns; all incoming evidence must match first."""
    root = Path(root or ROOT)
    review = load_reviews(root)
    if not review["record"]:
        raise ValueError("A verified human decision record is required")
    prepared = []
    for relative, batch in [("results/event_original_four_human_review.csv", "original"),
                            ("results/event_extraction_additional_review.csv", "supplemental")]:
        with (root / relative).open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        for row in rows:
            entry = review["events"][row["source_id"]]
            if entry["batch"] != batch or row["source_url"] != entry["document"]["source_url"] or row["input_excerpt"] != entry["document"]["source_text"]:
                raise ValueError("Review CSV input does not match verified evidence")
            decision = entry["decision"]
            if batch == "original":
                field = row["field"]
                reference = entry["document"]["human_gold"][field]
                if json.loads(row["actual_llm_output"]) != entry["output"][field] or json.loads(row["provisional_reference"]) != reference:
                    raise ValueError("Original CSV field evidence mismatch")
                verdict = "ACCEPTED_CORE_FIELD"
                if row["source_id"] == "cambridge_science_2026" and field == "location":
                    verdict = "SEMANTICALLY_ACCEPTED_SUPPORTED_ADDRESS_EXPANSION"
                row.update(human_judgment=verdict, reviewer=REVIEWER,
                           notes=" ".join(annotation_lines(entry, review["record"])))
            else:
                if row["output_sha256"] != decision["output_sha256"] or json.loads(row["llm_output_json"]) != entry["output"]:
                    raise ValueError("Supplemental CSV output evidence mismatch")
                row.update(human_judgment=decision["human_judgment"],
                           human_reviewer=REVIEWER,
                           human_review_notes=" ".join(annotation_lines(entry, review["record"])))
            row.update(human_review_status="ADJUDICATED",
                       review_method=METHOD,
                       record_compiled_date_jst=review["record"]["record_compiled_date_jst"],
                       adjudicated_at="", case_judgment=decision["human_judgment"],
                       output_sha256=decision["output_sha256"],
                       remediation_status="SEPARATE_ANNOTATION_APPLIED; RAW_OUTPUT_UNCHANGED")
        prepared.append((root / relative, rows))
    # All source/field checks complete before either CSV is touched.
    for path, rows in prepared:
        import io
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=list(dict.fromkeys(k for row in rows for k in row)))
        writer.writeheader()
        writer.writerows(rows)
        # Named review fields are an authorized update; regenerated evidence uses write_review_csv.
        path.write_text(stream.getvalue(), encoding="utf-8", newline="")
    return review
