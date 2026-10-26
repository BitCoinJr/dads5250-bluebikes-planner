"""Evidence-grounded event extraction and explicitly assumed demand scenarios.

The offline path loads agent-authored contract fixtures, never calls these LLM outputs,
and never reports fixture agreement as model accuracy. No framework is needed.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from jsonschema import Draft202012Validator, FormatChecker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OPENAI_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-4.1-mini"
RECORDED_FILENAME = "event_extraction_live.json"
SCORED_FIELDS = ("start_date", "end_date", "location", "city", "expected_crowd_size")


def _root(root=None) -> Path:
    return Path(root) if root is not None else PROJECT_ROOT


def _project_env(root=None) -> dict:
    """Read only the two supported names from the ignored project .env file.

    This deliberately is not a shell evaluator. No interpolation or commands
    are supported. Values are never included in logs or exceptions.
    """
    path = _root(root) / ".env"
    if not path.is_file():
        return {}
    if path.stat().st_size > 131072:
        raise ValueError("Project .env is unexpectedly large; contents withheld")
    result = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        name, value = name.strip(), value.strip()
        if name not in {"OPENAI_API_KEY", "OPENAI_MODEL"}:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        result[name] = value
    return result


def _windows_user_env() -> dict:
    """Read persisted user-level OpenAI settings when this process predates them."""
    if os.name != "nt":
        return {}
    import winreg
    result = {}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
            for name in ("OPENAI_API_KEY", "OPENAI_MODEL"):
                try:
                    value, _ = winreg.QueryValueEx(handle, name)
                    if isinstance(value, str):
                        result[name] = value
                except FileNotFoundError:
                    pass
    except OSError:
        pass
    return result


def _configuration(root=None) -> dict:
    local, persisted = _project_env(root), _windows_user_env()
    sources = [("process_environment", os.environ), ("project_dotenv", local),
               ("windows_user_environment", persisted)]
    key, key_source = None, "none"
    for source, values in sources:
        candidate = values.get("OPENAI_API_KEY", "").strip()
        if candidate and candidate not in {"your_openai_api_key_here", "REPLACE_ME"}:
            key, key_source = candidate, source
            break
    model = next((values["OPENAI_MODEL"].strip() for _, values in sources
                  if values.get("OPENAI_MODEL", "").strip()), DEFAULT_MODEL)
    if not re.fullmatch(r"[A-Za-z0-9._:-]{1,100}", model) or model.startswith("sk-"):
        raise ValueError("Invalid OPENAI_MODEL setting; value withheld")
    return {"api_key": key, "key_source": key_source, "model": model}


def check_config(root=None) -> dict:
    """Return safe presence/source metadata, never credential values."""
    settings = _configuration(root)
    return {"provider": "openai", "key_present": bool(settings["api_key"]),
            "key_source": settings["key_source"], "model": settings["model"],
            "endpoint": OPENAI_URL, "sdk_required": False}


def _hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def load_documents(root=None) -> list[dict]:
    """Load short real-source excerpts plus provisional agent draft annotations."""
    return json.loads((_root(root) / "fixtures/event_documents.json").read_text(encoding="utf-8"))


def event_schema(root=None) -> dict:
    return json.loads((_root(root) / "prompts/event_schema.json").read_text(encoding="utf-8"))


def validate_event(record: dict, document: dict | None = None, root=None) -> dict:
    """Check schema, chronology, URL provenance, and literal evidence grounding.

    These checks catch structural and simple provenance failures. They do not
    establish that all the model's semantic interpretations are true.
    """
    Draft202012Validator(event_schema(root), format_checker=FormatChecker()).validate(record)
    if record["start_date"] and record["end_date"]:
        if date.fromisoformat(record["end_date"]) < date.fromisoformat(record["start_date"]):
            raise ValueError("Event end precedes start")
    if document is not None:
        if record["source_url"] != document["source_url"]:
            raise ValueError("Model changed the source URL")
        if record["evidence_text"] not in document["source_text"]:
            raise ValueError("Evidence must be a literal excerpt from the supplied source text")
        if record["expected_crowd_size"] is not None:
            # Numeric evidence is necessary but is not sufficient semantic proof.
            number = str(record["expected_crowd_size"])
            if number not in record["evidence_text"].replace(",", ""):
                raise ValueError("Crowd estimate requires its number in the evidence")
    return record


def load_fixture_events(root=None) -> list[dict]:
    """Return AGENT-AUTHORED expected records, for offline contract testing only."""
    records = []
    for document in load_documents(root):
        record = copy.deepcopy(document["human_gold"])
        validate_event(record, document, root)
        records.append(record)
    return records


def extraction_payload(document: dict, model: str | None = None, root=None) -> dict:
    """Build the reviewable API request without credentials."""
    system_prompt = (_root(root) / "prompts/event_extraction_v1.txt").read_text(encoding="utf-8")
    user = {
        "source_url": document["source_url"],
        "source_title": document["source_title"],
        "source_text": document["source_text"],
    }
    # Use the portable Structured Outputs subset remotely; retain stronger date,
    # URI, numeric and string constraints in the full local JSON Schema validator.
    def supported_schema(node):
        if isinstance(node, dict):
            return {key: supported_schema(value) for key, value in node.items()
                    if key not in {"$schema", "title", "format", "pattern", "minimum", "minLength"}}
        if isinstance(node, list):
            return [supported_schema(value) for value in node]
        return node
    return {
        "model": model or _configuration(root)["model"],
        "input": [{"role": "system", "content": system_prompt},
                  {"role": "user", "content": json.dumps(user, ensure_ascii=False)}],
        "text": {"format": {"type": "json_schema", "name": "bluebikes_event", "strict": True,
                            "schema": supported_schema(event_schema(root))}},
        "store": False,
        "temperature": 0,
        "max_output_tokens": 1800,
    }


def extract_event(document: dict, *, api_key: str | None = None,
                  model: str | None = None, root=None, session=None) -> tuple[dict, dict]:
    """Make one actual OpenAI Responses API call; never substitute a fixture.

    The URL is fixed so a custom endpoint cannot accidentally receive a key.
    HTTP exception text intentionally omits response bodies and credentials.
    """
    key = api_key or _configuration(root)["api_key"]
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not configured; live LLM extraction is blocked")
    payload = extraction_payload(document, model, root)
    client = session or requests.Session()
    started = time.perf_counter()
    response = client.post(OPENAI_URL, headers={"Authorization": "Bearer " + key},
                           json=payload, timeout=(15, 60), allow_redirects=False)
    if response.status_code != 200:
        raise RuntimeError(f"OpenAI returned HTTP {response.status_code}; response body withheld")
    body = response.json()
    if body.get("status") != "completed" or body.get("error"):
        raise ValueError("OpenAI response did not complete; no extraction accepted")
    texts = []
    for item in body.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "refusal":
                raise ValueError("OpenAI refused extraction; refusal content withheld")
            if content.get("type") == "output_text":
                texts.append(content.get("text", ""))
    if not texts or not "".join(texts).strip():
        raise ValueError("OpenAI returned no structured output text")
    record = json.loads("".join(texts))
    validate_event(record, document, root)
    metadata = {
        "source_id": document["id"], "provider": "openai", "mode": "live", "endpoint": OPENAI_URL,
        "model": body.get("model", payload["model"]), "usage": body.get("usage"),
        "requested_model": payload["model"], "response_id": body.get("id"),
        "request_sha256": _hash(payload), "output_sha256": _hash(record),
        "response_status": body["status"], "latency_seconds": round(time.perf_counter() - started, 3),
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    return record, metadata


def evaluate_extractions(records: list[dict], documents: list[dict]) -> dict:
    """Exact-match scores against provisional agent draft reference labels.

    Location exact-match is strict and can penalize equivalent wording. Four
    examples are a smoke evaluation, not a reliable generalization estimate.
    """
    if len(records) != len(documents):
        raise ValueError("One extraction per gold document is required")
    rows = []
    for prediction, doc in zip(records, documents):
        validate_event(prediction, doc)
        gold = doc["human_gold"]
        for field in SCORED_FIELDS:
            rows.append({"source_id": doc["id"], "field": field,
                         "correct": prediction[field] == gold[field],
                         "expected": gold[field], "predicted": prediction[field]})
    correct = sum(row["correct"] for row in rows)
    return {"metric": "field_exact_match", "examples": len(records),
            "reference_status": "provisional_agent_draft_labels_human_review_pending",
            "correct_fields": correct, "total_fields": len(rows),
            "accuracy": correct / len(rows) if rows else None, "details": rows}


def _recorded_extraction(documents, root=None) -> dict:
    path = _root(root) / "results" / RECORDED_FILENAME
    if not path.is_file():
        return {"status": "blocked_missing_recorded_outputs", "mode": "recorded", "provider": "openai",
                "events": [], "api_calls": 0, "live_llm_verified": False,
                "evaluation": {"status": "not_run", "accuracy": None,
                               "reason": "No completed live OpenAI extraction artifact exists"}}
    saved = json.loads(path.read_text(encoding="utf-8"))
    records, calls = saved.get("events", []), saved.get("calls", [])
    if (saved.get("mode") != "live" or saved.get("status") != "completed"
            or saved.get("provider") != "openai" or not saved.get("live_llm_verified")
            or len(records) != len(documents) or len(calls) != len(documents)):
        raise ValueError("Recorded artifact is not a complete live OpenAI extraction")
    for document, record, call in zip(documents, records, calls):
        validate_event(record, document, root)
        payload = extraction_payload(document, model=call.get("requested_model"), root=root)
        if (call.get("source_id") != document["id"] or call.get("provider") != "openai"
                or call.get("endpoint") != OPENAI_URL or call.get("mode") != "live"
                or call.get("response_status") != "completed" or not call.get("response_id")
                or call.get("request_sha256") != _hash(payload)
                or call.get("output_sha256") != _hash(record)):
            raise ValueError("Recorded extraction provenance/hash mismatch; rerun live explicitly")
    return {**saved, "status": "recorded_live_outputs_validated", "mode": "recorded",
            "api_calls": 0, "recorded_api_calls": saved["api_calls"],
            "recorded_artifact": "results/" + RECORDED_FILENAME,
            "evaluation": evaluate_extractions(records, documents)}


def run_extraction(mode="fixture", root=None) -> dict:
    """Fixtures, actual API execution, or validated recorded live outputs.

    The live mode automatically persists a complete credential-free artifact.
    Recorded mode makes no API calls and never silently substitutes fixtures.
    """
    documents = load_documents(root)
    if mode == "fixture":
        events = load_fixture_events(root)
        return {"status": "fixture_contract_validated", "mode": "fixture", "provider": "openai",
                "events": events, "api_calls": 0,
                "evaluation": {"status": "not_run", "accuracy": None,
                               "reason": "Agent-authored contract fixtures are not LLM predictions or human-reviewed gold"},
                "fixture_schema_valid_count": len(events),
                "live_llm_verified": False}
    if mode == "recorded":
        return _recorded_extraction(documents, root)
    if mode != "live":
        raise ValueError("mode must be fixture, live or recorded")
    settings = _configuration(root)
    if not settings["api_key"]:
        return {"status": "blocked_missing_api_key", "mode": "live", "provider": "openai", "events": [],
                "api_calls": 0, "live_llm_verified": False,
                "evaluation": {"status": "not_run", "accuracy": None,
                               "reason": "OPENAI_API_KEY is not configured"}}
    records, calls = [], []
    for document in documents:
        record, metadata = extract_event(document, api_key=settings["api_key"], model=settings["model"], root=root)
        records.append(record)
        calls.append(metadata)
    result = {"status": "completed", "mode": "live", "provider": "openai", "events": records,
            "api_calls": len(calls), "calls": calls, "live_llm_verified": True,
            "evaluation": evaluate_extractions(records, documents)}
    path = _root(root) / "results" / RECORDED_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def event_adjustments(forecast: pd.DataFrame, event_records: list[dict],
                      extra_moves_per_event: float = 0.0) -> pd.DataFrame:
    """Apply a declared incremental scenario once per event across its months.

    Required forecast columns: year, month, city, demand_bikes. An event's total
    assumed increment is prorated over calendar days if it crosses months. Null
    date/city events are excluded. Negative or non-finite assumptions are invalid.
    Recurrent effects already in seasonality should get zero incremental moves.
    This is NOT a fitted causal effect, nor an observation of operational moves.
    """
    if not math.isfinite(extra_moves_per_event) or extra_moves_per_event < 0:
        raise ValueError("extra_moves_per_event must be finite and nonnegative")
    required = {"year", "month", "city", "demand_bikes"}
    if not required.issubset(forecast.columns):
        raise ValueError(f"Missing forecast columns: {sorted(required - set(forecast.columns))}")
    if forecast.duplicated(["year", "month", "city"]).any():
        raise ValueError("Forecast must have one row per city/month")
    result = forecast.copy()
    result["base_demand_bikes"] = result["demand_bikes"]
    result["event_increment_bikes"] = 0.0
    result["event_count"] = 0
    # URL/name/date identity prevents accidentally adding a duplicated extraction.
    seen = set()
    for event in event_records:
        validate_event(event)
        start = event["start_date"]
        if not start or not event["city"]:
            continue
        identity = (event["source_url"], event["event_name"], start, event["end_date"])
        if identity in seen:
            continue
        seen.add(identity)
        days = pd.date_range(start, event["end_date"] or start, freq="D")
        periods = pd.Series(days.to_period("M")).value_counts()
        for period, count in periods.items():
            mask = ((result["year"] == period.year) & (result["month"] == period.month)
                    & (result["city"] == event["city"]))
            result.loc[mask, "event_increment_bikes"] += extra_moves_per_event * count / len(days)
            result.loc[mask, "event_count"] += 1
    result["demand_bikes"] = result["base_demand_bikes"] + result["event_increment_bikes"]
    result.attrs["event_adjustment_assumption"] = {
        "extra_moves_per_event": extra_moves_per_event,
        "status": "uncalibrated incremental scenario; zero by default",
        "availability": "Retrospective source retrieval; not a Jan-2026 available-information backtest",
    }
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["fixture", "live", "recorded"], default="fixture")
    parser.add_argument("--check-config", action="store_true", help="Print safe key presence/source metadata only")
    parser.add_argument("--output", type=Path, help="Write result JSON, without API credentials")
    args = parser.parse_args()
    if args.check_config:
        print(json.dumps(check_config(), indent=2))
        return
    result = run_extraction(args.mode)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in {"events", "calls"}}, indent=2))


if __name__ == "__main__":
    main()
