"""Regenerate automatic review evidence while retaining human-entered work."""
from __future__ import annotations

import csv
from pathlib import Path
import uuid

HUMAN_DEFAULTS = {"human_judgment": "", "reviewer": "", "notes": "", "human_review_status": "PENDING",
                  "human_reviewer": "", "human_review_notes": ""}
KEY_FIELDS = ("source_id", "field")


def _strings(row):
    return {key: "" if value is None else str(value) for key, value in row.items()}


def _index(rows, key_fields, origin):
    result = {}
    for row in rows:
        if any(not row.get(field, "") for field in key_fields):
            raise ValueError(f"{origin} review row lacks a nonempty identity field")
        key = tuple(row[field] for field in key_fields)
        if key in result:
            raise ValueError(f"Duplicate {origin} review identity: {key!r}")
        result[key] = row
    return result


def _has_human_work(row, protected_columns):
    for column in protected_columns:
        value = row.get(column, "").strip()
        if column == "human_review_status":
            if value and value.upper() != "PENDING":
                return True
        elif value:
            return True
    return False


def write_review_csv(path, rows, *, key_fields=KEY_FIELDS):
    """Preserve judgments only for identical evidence; reject destructive changes.

    The generated identity is source_id + field by default. Every other incoming
    non-human column (including batch, URL, input, reference, output and automatic
    score) is evidence and must match before an existing judgment can be reused.
    Existing extra columns are conservatively treated as user-owned. A reviewed
    changed/removed row raises before any file replacement. Unreviewed changed
    rows can be regenerated. Empty input is a no-op, so fixture mode cannot erase
    an existing real-output review sheet.
    """
    path = Path(path)
    incoming = [_strings(row) for row in rows]
    if not incoming:
        return {"rows_written": 0, "preserved_review_rows": 0, "skipped_empty": True}
    generated_columns = list(dict.fromkeys(column for row in incoming for column in row))
    evidence_columns = [column for column in generated_columns if column not in HUMAN_DEFAULTS]
    incoming_by_key = _index(incoming, key_fields, "incoming")
    existing, old_columns = [], []
    if path.is_file():
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            old_columns = reader.fieldnames or []
            existing = list(reader)
        if any(field not in old_columns for field in key_fields):
            raise ValueError("Existing review CSV has no usable identity header; preserve it for manual inspection")
        if any(None in row for row in existing):
            raise ValueError("Existing review CSV has malformed extra cells; refusing to replace it")
    old_by_key = _index(existing, key_fields, "existing")
    extra_columns = [column for column in old_columns if column not in generated_columns and column not in HUMAN_DEFAULTS]
    protected_columns = list(HUMAN_DEFAULTS) + extra_columns
    for key, old in old_by_key.items():
        new = incoming_by_key.get(key)
        changed = new is None or any(old.get(column, "") != new.get(column, "") for column in evidence_columns)
        if changed and _has_human_work(old, protected_columns):
            action = "remove" if new is None else "replace changed evidence for"
            raise ValueError(f"Refusing to {action} a row with human review work: {key!r}; version the sheet explicitly")
    merged, preserved = [], 0
    for key, row in incoming_by_key.items():
        new = dict(row)
        for column, default in HUMAN_DEFAULTS.items():
            new.setdefault(column, default)
        old = old_by_key.get(key)
        same = old is not None and all(old.get(column, "") == row.get(column, "") for column in evidence_columns)
        if same:
            for column in protected_columns:
                if column in old:
                    new[column] = old[column]
            preserved += int(_has_human_work(old, protected_columns))
        else:
            for column in extra_columns:
                new.setdefault(column, "")
        merged.append(new)
    columns = list(dict.fromkeys(generated_columns + list(HUMAN_DEFAULTS) + extra_columns))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(merged)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {"rows_written": len(merged), "preserved_review_rows": preserved, "skipped_empty": False}
