"""Supplemental audience/participant extraction; never overwrite the original run.

References are AI drafts frozen before live calls. Human review remains pending.
The two positive excerpts describe the same event and are not independent cases.
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .events import (OPENAI_URL, PROJECT_ROOT, SCORED_FIELDS, _configuration,
                     _hash, extract_event, extraction_payload, validate_event)

DOCUMENTS = "fixtures/event_documents_additional.json"
LIVE = "results/event_extraction_additional_live.json"
FREEZE = "results/event_extraction_additional_freeze.json"
EVALUATION = "results/event_extraction_additional_evaluation.json"
REVIEW_CSV = "results/event_extraction_additional_review.csv"
REVIEW_DOC = "docs/human_review_additional.md"
ORIGINALS = ["fixtures/event_documents.json", "prompts/event_extraction_v1.txt",
             "prompts/event_schema.json", "results/event_extraction_live.json"]


def _root(root=None):
    return Path(root) if root is not None else PROJECT_ROOT


def _read(root, name):
    return json.loads((root / name).read_text(encoding="utf-8-sig"))


def _save(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def load_additional_documents(root=None):
    docs = _read(_root(root), DOCUMENTS)
    if len({doc["id"] for doc in docs}) != len(docs):
        raise ValueError("Duplicate supplemental source ID")
    for doc in docs:
        validate_event(doc["reference"], doc, root)
        if doc["reference"]["expected_crowd_size"] != doc["crowd_reference"]["value"]:
            raise ValueError("Crowd reference annotation disagrees with the draft record")
    return docs


def _input_hashes(root):
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in ORIGINALS + [DOCUMENTS]}


def freeze_references(root=None):
    """Persist pre-call hashes or reject changes to an already-frozen run."""
    root = _root(root)
    docs = load_additional_documents(root)
    hashes = _input_hashes(root)
    if (root / FREEZE).is_file():
        manifest = _read(root, FREEZE)
        if manifest.get("files_sha256") != hashes:
            raise ValueError("Frozen supplemental/original inputs changed; version a new evaluation instead")
        return manifest
    original = _read(root, "results/event_extraction_live.json")
    manifest = {
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_ids": [doc["id"] for doc in docs], "files_sha256": hashes,
        "reference_status": "AI-authored draft frozen before calls; actual human review pending",
        "original_baseline": {key: original["evaluation"][key]
                              for key in ["correct_fields", "total_fields", "accuracy"]},
    }
    _save(root, FREEZE, manifest)
    return manifest


def evaluate_additional(records, docs):
    if len(records) != len(docs):
        raise ValueError("One supplemental prediction per source is required")
    details, audience_checks, quality_notes = [], [], []
    for record, doc in zip(records, docs):
        validate_event(record, doc)
        reference = doc["reference"]
        for field in SCORED_FIELDS:
            details.append({"source_id": doc["id"], "field": field,
                            "expected": reference[field], "predicted": record[field],
                            "exact_match": reference[field] == record[field]})
        number = record["expected_crowd_size"]
        non_audience = [entry["value"] for entry in doc["non_audience_numbers"]]
        audience_checks.append({
            "source_id": doc["id"], "case_type": doc["case_type"],
            "expected_crowd_reference": doc["crowd_reference"],
            "predicted_crowd_value": number,
            "crowd_matches_draft": number == reference["expected_crowd_size"],
            "non_audience_numbers": doc["non_audience_numbers"],
            "non_audience_number_used_as_crowd": number is not None and number in non_audience,
            "qualifier_in_model_ambiguities": any(
                phrase in " ".join(record["ambiguities"]).lower()
                for phrase in (["more than", "over", "lower bound", "lower-bound"]
                               if doc["crowd_reference"]["qualifier"] == "more than"
                               else ["approximately", "approximate", "about", "estimated", "estimate"]))
                if doc["crowd_reference"]["qualifier"] else None,
        })
        check = audience_checks[-1]
        if check["non_audience_number_used_as_crowd"]:
            quality_notes.append({"source_id": doc["id"], "flag": "non_audience_number_used_as_crowd",
                                  "detail": "The predicted crowd equals a source number annotated as participants/competitors/volunteers, not audience."})
        if doc["crowd_reference"]["qualifier"] and not check["qualifier_in_model_ambiguities"]:
            quality_notes.append({"source_id": doc["id"], "flag": "crowd_qualifier_omitted_from_ambiguities",
                                  "detail": "The model ambiguity prose omits the source qualifier '" + doc["crowd_reference"]["qualifier"] + "'. It remains in the source/reference annotation; the bare integer is not an exact attendance claim."})
        for date_field in ("start_date", "end_date"):
            if reference[date_field] is None and record[date_field] is not None:
                quality_notes.append({"source_id": doc["id"], "flag": "unsupported_date_inference",
                                      "field": date_field, "predicted": record[date_field],
                                      "detail": "A date was supplied despite the frozen excerpt/reference not establishing an event day. This is an automated grounding flag, not a human judgment."})
        ambiguity_text = " ".join(record["ambiguities"]).lower()
        if "multiple municipalities" in ambiguity_text and "municipal" not in doc["source_text"].lower():
            quality_notes.append({"source_id": doc["id"], "flag": "geographic_explanation_requires_review",
                                  "detail": "The ambiguity prose asserts multiple municipalities beyond the wording of the supplied excerpt; inspect for prior-knowledge inference."})
    correct = sum(row["exact_match"] for row in details)
    positives = [row for row in audience_checks if row["case_type"] == "audience_and_participants"]
    negatives = [row for row in audience_checks if row["case_type"] == "participants_only"]
    return {"metric": "exact agreement with frozen supplemental AI draft references",
            "reference_status": "provisional_agent_draft_labels_human_review_pending",
            "examples": len(docs), "distinct_events": len({doc["event_identity"] for doc in docs}),
            "positive_audience_examples": len(positives), "participant_only_examples": len(negatives),
            "correct_fields": correct, "total_fields": len(details),
            "exact_agreement": correct / len(details) if details else None,
            "by_field": [{"field": field, "matching": sum(row["exact_match"] for row in details if row["field"] == field),
                          "total": sum(row["field"] == field for row in details)} for field in SCORED_FIELDS],
            "details": details, "disagreements": [row for row in details if not row["exact_match"]],
            "automated_quality_notes": quality_notes,
            "automated_notes_are_human_judgments": False,
            "audience_checks": audience_checks,
            "positive_crowd_matches": sum(row["crowd_matches_draft"] for row in positives),
            "participant_only_null_matches": sum(row["predicted_crowd_value"] is None for row in negatives),
            "non_audience_substitutions": sum(row["non_audience_number_used_as_crowd"] for row in audience_checks),
            "human_review_complete": False,
            "limitations": ["AI-authored references, not human-reviewed truth", "Two positive texts concern the same HOCR event and are correlated",
                            "Source-specific approximate/lower-bound audience figures are not actual measured attendance",
                            "The integer schema cannot encode a quantity qualifier; visible source/reference annotations retain it",
                            "Supplemental cases never enter demand forecasts or staffing and do not duplicate event increments"]}


def _export_review(root, docs, result):
    """Retain human-entered review fields on a same-output recorded rerun."""
    old = {}
    path = root / REVIEW_CSV
    if path.is_file():
        with path.open(encoding="utf-8-sig", newline="") as handle:
            old = {row["source_id"]: row for row in csv.DictReader(handle)}
    rows = []
    for doc, prediction in zip(docs, result["events"]):
        previous = old.get(doc["id"], {})
        if previous and previous.get("output_sha256") != _hash(prediction):
            raise ValueError("Review CSV belongs to different outputs; preserve/version human work before replacing it")
        rows.append({"source_id": doc["id"], "source_url": doc["source_url"],
                     "input_excerpt": doc["source_text"],
                     "reference_json": json.dumps(doc["reference"], ensure_ascii=False, sort_keys=True),
                     "llm_output_json": json.dumps(prediction, ensure_ascii=False, sort_keys=True),
                     "crowd_qualifier_annotation": json.dumps(doc["crowd_reference"], ensure_ascii=False),
                     "automated_quality_notes": json.dumps([note for note in result["evaluation"]["automated_quality_notes"]
                                                             if note["source_id"] == doc["id"]], ensure_ascii=False),
                     "output_sha256": _hash(prediction),
                     "human_judgment": previous.get("human_judgment", ""),
                     "human_reviewer": previous.get("human_reviewer", ""),
                     "human_review_notes": previous.get("human_review_notes", ""),
                     "human_review_status": previous.get("human_review_status", "PENDING")})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["source_id"])
        writer.writeheader()
        writer.writerows(rows)
    # The CSV is the human-input surface. Preserve any existing Markdown review.
    if not (root / REVIEW_DOC).exists():
        lines = ["# Supplemental event extraction human review", "",
                 "**PENDING: no actual human judgment has been entered or claimed.** The input excerpts and AI draft references were frozen before the separate API run. The original four-case 19/20 baseline is unchanged.", "",
                 "Use [the review CSV](../results/event_extraction_additional_review.csv) to enter human_judgment, human_reviewer and human_review_notes. Leave the original AI reference and model output intact. Qualifiers are part of the fact: a lower bound or approximate figure must not become an exact attendance claim.", "",
                 "| Case | Input excerpt | Draft reference (five scored fields) | LLM output (five scored fields) | Human judgment |",
                 "|---|---|---|---|---|"]
        for doc, prediction in zip(docs, result["events"]):
            ref = {key: doc["reference"][key] for key in SCORED_FIELDS}
            pred = {key: prediction[key] for key in SCORED_FIELDS}
            values = [doc["id"], doc["source_text"], json.dumps(ref, ensure_ascii=False), json.dumps(pred, ensure_ascii=False), "PENDING"]
            lines.append("| " + " | ".join(value.replace("|", "\\|").replace("\n", " ") for value in values) + " |")
        lines += ["", "Two positive sources describe the same Head Of The Charles event; they are correlated and their audience estimates are source-specific. The participant-only case must keep audience null. This is a supplemental text test, not new forecasting demand or an allocation of audience to a city.", "",
                  "Review dates and venue/city evidence, spectator-versus-participant roles, quantity qualifiers and any unsupported ambiguity prose. Automatic exact-match agreement is not human evaluation. Additional source details: [event_sources_additional.md](event_sources_additional.md)."]
        (root / REVIEW_DOC).parent.mkdir(parents=True, exist_ok=True)
        (root / REVIEW_DOC).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _finish(root, docs, result):
    evaluation = evaluate_additional(result["events"], docs)
    result["evaluation"] = evaluation
    _save(root, EVALUATION, {"status": result["status"], "mode": result["mode"],
                            "api_calls_this_run": result["api_calls"],
                            "original_additional_api_calls": result.get("recorded_api_calls", result["api_calls"]),
                            **evaluation})
    _export_review(root, docs, result)
    return result


def run_additional_evaluation(mode="recorded", root=None):
    root = _root(root)
    docs = load_additional_documents(root)
    if mode not in {"live", "recorded"}:
        raise ValueError("Supplemental mode must be live or recorded; no fixture fallback")
    if mode == "recorded":
        if not (root / LIVE).is_file():
            return {"status": "blocked_missing_additional_live_outputs", "mode": "recorded", "api_calls": 0,
                    "events": [], "live_llm_verified": False}
        saved, manifest = _read(root, LIVE), _read(root, FREEZE)
        if manifest.get("files_sha256") != _input_hashes(root):
            raise ValueError("Frozen inputs changed; supplemental replay rejected")
        if (saved.get("status") != "completed" or saved.get("mode") != "live"
                or saved.get("provider") != "openai" or not saved.get("live_llm_verified")
                or saved.get("frozen_manifest_sha256") != _hash(manifest)
                or len(saved.get("events", [])) != len(docs) or len(saved.get("calls", [])) != len(docs)):
            raise ValueError("Supplemental artifact is not a complete live API run")
        for doc, prediction, call in zip(docs, saved["events"], saved["calls"]):
            validate_event(prediction, doc, root)
            if (call.get("source_id") != doc["id"] or call.get("provider") != "openai"
                    or call.get("endpoint") != OPENAI_URL or call.get("mode") != "live"
                    or call.get("response_status") != "completed" or not call.get("response_id")
                    or call.get("request_sha256") != _hash(extraction_payload(doc, call["requested_model"], root))
                    or call.get("output_sha256") != _hash(prediction)):
                raise ValueError("Supplemental live output provenance/hash mismatch")
        return _finish(root, docs, {**saved, "status": "recorded_additional_live_outputs_validated",
                                   "mode": "recorded", "api_calls": 0, "recorded_api_calls": saved["api_calls"]})
    settings = _configuration(root)
    if not settings["api_key"]:
        return {"status": "blocked_missing_api_key", "mode": "live", "api_attempts": 0, "api_calls": 0,
                "events": [], "live_llm_verified": False}
    manifest = freeze_references(root)
    result = {"status": "in_progress", "mode": "live", "provider": "openai", "api_attempts": 0,
              "api_calls": 0, "events": [], "calls": [], "attempts": [], "live_llm_verified": False,
              "frozen_manifest_sha256": _hash(manifest), "used_for_forecast_or_staffing": False}
    for doc in docs:
        attempt = {"source_id": doc["id"], "started_at_utc": datetime.now(timezone.utc).isoformat(), "status": "started"}
        result["attempts"].append(attempt)
        result["api_attempts"] += 1
        _save(root, LIVE, result)
        try:
            prediction, call = extract_event(doc, api_key=settings["api_key"], model=settings["model"], root=root)
        except Exception as error:
            attempt.update({"status": "failed", "error_type": type(error).__name__,
                            "reason": "API request or local validation failed; no fixture substitution"})
            result["status"] = "failed"
            _save(root, LIVE, result)
            raise RuntimeError("Supplemental live extraction failed; redacted attempt metadata saved") from None
        result["events"].append(prediction)
        result["calls"].append(call)
        result["api_calls"] += 1
        attempt["status"] = "validated_success"
        _save(root, LIVE, result)
    if _input_hashes(root) != manifest["files_sha256"]:
        raise RuntimeError("Original or supplemental frozen inputs changed during API execution")
    result.update({"status": "completed", "live_llm_verified": True})
    _finish(root, docs, result)
    _save(root, LIVE, result)
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["live", "recorded"], default="recorded")
    args = parser.parse_args()
    result = run_additional_evaluation(args.mode)
    print(json.dumps({key: result.get(key) for key in ["status", "mode", "api_attempts", "api_calls", "recorded_api_calls", "live_llm_verified"]}, indent=2))
    if "evaluation" in result:
        evaluation = result["evaluation"]
        print(json.dumps({key: evaluation[key] for key in ["examples", "distinct_events", "correct_fields", "total_fields", "exact_agreement", "positive_crowd_matches", "participant_only_null_matches", "non_audience_substitutions", "human_review_complete"]}, indent=2))


if __name__ == "__main__":
    main()
