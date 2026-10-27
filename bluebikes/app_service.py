"""Read-only, session-scoped backend for the optional event planning demo.

No extraction/evaluation artifacts or review sheets are written. A real API call
occurs only in extract_live(), using the project's ignored .env credential.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import date
import hashlib
import hmac
import json
import math
from pathlib import Path
import re
import secrets

import pandas as pd

from .events import (
    DEFAULT_MODEL, OPENAI_URL, _hash, _project_env, event_adjustments,
    extract_event, extraction_payload, validate_event,
)
from .planner import CORE_CITIES, OTHER_POOL, PlannerConfig, baseline_plan, plan_crews
from .scenarios import _chain, _period_row


DOC_FIELDS = ("id", "source_title", "source_url", "source_text")
EVALUATION_ONLY_MESSAGE = ("Evaluation only — excluded from staffing plans. "
                           "These supplemental cases test extraction quality only; editing or confirming "
                           "their fields does not make them planning inputs.")
EDIT_FIELDS = ("start_date", "end_date", "city", "location", "expected_crowd_size", "ambiguities")


class _InputError(ValueError):
    """Only messages explicitly authored here may be shown to the UI."""


def _document(value):
    if not isinstance(value, dict):
        raise _InputError("A source document is required.")
    result = {key: value.get(key, "user_input" if key == "id" else "") for key in DOC_FIELDS}
    if any(not isinstance(v, str) for v in result.values()):
        raise _InputError("Source fields must be text.")
    if not result["id"]:
        result["id"] = "user_input"
    if not result["source_title"].strip() or not result["source_text"].strip():
        raise _InputError("Source title and excerpt are required.")
    if not re.fullmatch(r"https://[^\s]+", result["source_url"]):
        raise _InputError("Source URL must be a nonempty https URL.")
    return result


def _clean_frame(frame):
    return frame.astype(object).where(pd.notna(frame), None).to_dict("records")


class AppService:
    def __init__(self, root=None):
        self.root = Path(root) if root else Path(__file__).resolve().parents[1]
        self._secret = secrets.token_bytes(32)
        self._docs = []
        for filename, batch in [("event_documents.json", "original"),
                                ("event_documents_additional.json", "supplemental")]:
            for doc in self._read("fixtures/" + filename):
                self._docs.append({**deepcopy(doc), "_batch": batch})
        self._forecast = pd.read_csv(self.root / "results/forecast_2026.csv")
        monthly = pd.read_csv(self.root / "data/processed/monthly.csv")
        self._actual = monthly[(monthly.year == 2026) & monthly.month.between(1, 9)].copy()
        self._initial = pd.read_csv(self.root / "results/baseline_2026.csv")
        self._proposal = pd.read_csv(self.root / "results/plan_2026.csv")
        self._cfg = PlannerConfig()
        self._base_cache = {1: (self._initial.copy(deep=True), self._proposal.copy(deep=True))}

    def _read(self, relative):
        return json.loads((self.root / relative).read_text(encoding="utf-8-sig"))

    def _sign(self, value):
        return hmac.new(self._secret, _hash(value).encode(), hashlib.sha256).hexdigest()

    def choices(self):
        return [(f"[{d['_batch']}] {d['source_title']}", d["id"]) for d in self._docs]

    def _origin_ok(self, state):
        origin = state.get("source_origin")
        if not isinstance(origin, dict) or not hmac.compare_digest(
                str(state.get("origin_seal", "")), self._sign(origin)):
            raise _InputError("Source origin is not valid for this server session.")

    def evaluation_only(self, state):
        """Resolve identity against the server registry, never edited event facts."""
        origin = state.get("source_origin") or {}
        ids = {origin.get("source_id"), (state.get("provenance") or {}).get("source_id")}
        return any(d["_batch"] == "supplemental" and d["id"] in ids for d in self._docs)

    def _new(self, document=None, prior=None):
        if isinstance(prior, dict) and "source_origin" in prior:
            # Preserve the original selection through input edits, failures and live calls.
            origin, seal = deepcopy(prior["source_origin"]), prior.get("origin_seal")
        else:
            source_id = document.get("id") if isinstance(document, dict) else None
            doc = next((d for d in self._docs if d["id"] == source_id), None)
            origin = {"source_id": source_id, "batch": doc["_batch"] if doc else "custom"}
            seal = self._sign(origin)
        result = {"document": deepcopy(document), "original_llm": None, "provenance": None,
                "reviewed_event": None, "review_digest": None, "review_notes": "",
                "extraction_input_digest": None, "extraction_seal": None,
                "result": None, "status": "awaiting_extraction", "error": None,
                "source_origin": origin, "origin_seal": seal}
        result["evaluation_only"] = self.evaluation_only(result)
        return result

    def select(self, id):
        doc = next((d for d in self._docs if d["id"] == id), None)
        if doc is None:
            state = self._new()
            state.update(status="selection_failed", error="Unknown source choice.")
            return state
        document = {k: doc[k] for k in DOC_FIELDS}
        return self.load_saved(self._new(document), document)

    def invalidate(self, state, currentdoc):
        try:
            document = _document(currentdoc)
        except _InputError as exc:
            result = self._new(deepcopy(currentdoc), state)
            result.update(status="input_changed", error=str(exc))
            return result
        if isinstance(state, dict) and state.get("document") == document:
            return deepcopy(state)
        result = self._new(document, state)
        result["status"] = "input_changed"
        return result

    def invalidate_review(self, state):
        result = deepcopy(state) if isinstance(state, dict) else self._new()
        result.update(reviewed_event=None, review_digest=None, review_notes="",
                      result=None, status="review_changed", error=None)
        return result

    def _accepted(self, document, record, call, status, prior):
        provenance = {key: deepcopy(call[key]) for key in [
            "source_id", "provider", "mode", "model", "requested_model", "response_id",
            "request_sha256", "output_sha256", "response_status", "usage",
            "executed_at_utc", "latency_seconds", "endpoint"] if key in call}
        result = self._new(document, prior)
        result.update(original_llm=deepcopy(record), provenance=provenance,
                      extraction_input_digest=_hash(document), status=status)
        # A saved match can resolve an edited/custom ID to a supplemental source.
        # Keep that restriction even after subsequent edits or a new live response.
        matched = next((d for d in self._docs
                        if d["id"] == provenance.get("source_id") and d["_batch"] == "supplemental"), None)
        if matched is not None and result["source_origin"]["batch"] != "supplemental":
            result["source_origin"] = {"source_id": matched["id"], "batch": matched["_batch"]}
            result["origin_seal"] = self._sign(result["source_origin"])
        result["extraction_seal"] = self._sign({
            "document": document, "record": record, "provenance": provenance,
            "source_origin": result["source_origin"]})
        result["evaluation_only"] = self.evaluation_only(result)
        return result

    def _saved_batch(self, batch):
        docs = [d for d in self._docs if d["_batch"] == batch]
        filename = "event_extraction_live.json" if batch == "original" else "event_extraction_additional_live.json"
        saved = self._read("results/" + filename)
        if (saved.get("status") != "completed" or saved.get("mode") != "live"
                or saved.get("provider") != "openai" or not saved.get("live_llm_verified")
                or len(saved.get("events", [])) != len(docs)
                or len(saved.get("calls", [])) != len(docs)):
            raise _InputError("Saved real API artifact is incomplete; no fixture fallback.")
        if batch == "supplemental":
            manifest = self._read("results/event_extraction_additional_freeze.json")
            for name, expected in manifest.get("files_sha256", {}).items():
                if hashlib.sha256((self.root / name).read_bytes()).hexdigest() != expected:
                    raise _InputError("Frozen source or original evidence changed; saved replay rejected.")
            if (not manifest.get("files_sha256")
                    or saved.get("frozen_manifest_sha256") != _hash(manifest)):
                raise _InputError("Supplemental freeze/hash mismatch; saved replay rejected.")
        for doc, record, call in zip(docs, saved["events"], saved["calls"]):
            validate_event(record, doc, self.root)
            requested_model = call.get("requested_model")
            if not requested_model:
                raise _InputError("Saved model provenance is missing.")
            if (call.get("source_id") != doc["id"] or call.get("provider") != "openai"
                    or call.get("endpoint") != OPENAI_URL or call.get("mode") != "live"
                    or call.get("response_status") != "completed" or not call.get("response_id")
                    or call.get("request_sha256") != _hash(extraction_payload(doc, requested_model, self.root))
                    or call.get("output_sha256") != _hash(record)):
                raise _InputError("Saved request/output provenance mismatch; replay rejected.")
        return list(zip(docs, saved["events"], saved["calls"]))

    def load_saved(self, state, input_doc):
        result = self._new(deepcopy(input_doc), state)
        try:
            document = _document(input_doc)
            result["document"] = document
            self._origin_ok(result)
            matching = [d for d in self._docs if all(
                d[key] == document[key] for key in ("source_url", "source_title", "source_text"))]
            if not matching:
                raise _InputError("No exact saved source URL/title/text match. Use explicit live extraction.")
            for doc, record, call in self._saved_batch(matching[0]["_batch"]):
                if doc["id"] == matching[0]["id"]:
                    metadata = {**call, "mode": "recorded"}
                    result = self._accepted(document, record, metadata, "saved_ready", result)
                    break
        except _InputError as exc:
            result.update(status="saved_failed", error=str(exc))
        except Exception:
            result.update(status="saved_failed", error="Saved evidence validation failed; no output accepted.")
        return result

    def extract_live(self, state, input_doc):
        result = self._new(deepcopy(input_doc), state)
        try:
            document = _document(input_doc)
            result["document"] = document
            self._origin_ok(result)
            # Explicit UI action only; never fall back to process/User credentials.
            local = _project_env(self.root)
            key = local.get("OPENAI_API_KEY", "").strip()
            if not key or key in {"your_openai_api_key_here", "REPLACE_ME"}:
                raise _InputError("Project .env has no configured OPENAI_API_KEY; live extraction is blocked.")
            model = local.get("OPENAI_MODEL", "").strip() or DEFAULT_MODEL
            if not re.fullmatch(r"[A-Za-z0-9._:-]{1,100}", model) or model.startswith("sk-"):
                raise _InputError("Project model configuration is invalid; value withheld.")
            record, metadata = extract_event(document, api_key=key, model=model, root=self.root)
            validate_event(record, document, self.root)
            return self._accepted(document, record, metadata, "live_ready", result)
        except _InputError as exc:
            result.update(status="live_failed", error=str(exc))
        except Exception:
            # Never expose provider/requests exception text or response bodies.
            result.update(status="live_failed",
                          error="Live extraction failed; no output accepted. Retry explicitly or load matching saved evidence.")
        return result

    def _extraction_ok(self, state, document):
        if not isinstance(state, dict) or not state.get("original_llm"):
            raise _InputError("Extract live or explicitly load matching saved evidence first.")
        if state.get("document") != document or state.get("extraction_input_digest") != _hash(document):
            raise _InputError("Source input changed. Extract or load it again, then review.")
        self._origin_ok(state)
        expected = self._sign({"document": document, "record": state["original_llm"],
                               "provenance": state.get("provenance"),
                               "source_origin": state["source_origin"]})
        if not hmac.compare_digest(str(state.get("extraction_seal", "")), expected):
            raise _InputError("Extraction state is not valid for this server session.")
        validate_event(state["original_llm"], document, self.root)

    def _review(self, state, edits, notes):
        if not isinstance(edits, dict) or not isinstance(notes, str):
            raise _InputError("Review edits must be fields and review notes must be text.")
        original = state["original_llm"]
        for key in set(edits) - set(EDIT_FIELDS):
            if key not in original or edits[key] != original[key]:
                raise _InputError("Source, evidence and event identity are read-only.")
        record = deepcopy(original)
        for field in EDIT_FIELDS:
            value = deepcopy(edits.get(field, original[field]))
            if field == "ambiguities":
                if isinstance(value, str):
                    value = [line.strip() for line in value.splitlines() if line.strip()]
            elif field == "expected_crowd_size":
                if value is None or value == "":
                    value = None
                else:
                    if isinstance(value, bool):
                        raise _InputError("Crowd must be a nonnegative whole number or null.")
                    if isinstance(value, str):
                        if not re.fullmatch(r"[0-9,]+", value.strip()):
                            raise _InputError("Crowd must be a nonnegative whole number or null.")
                        value = int(value.replace(",", ""))
                    if not isinstance(value, (int, float)) or not math.isfinite(value) or int(value) != value or value < 0:
                        raise _InputError("Crowd must be a nonnegative whole number or null.")
                    value = int(value)
            elif value is not None:
                if not isinstance(value, str):
                    raise _InputError("Reviewed dates, city and location must be text or null.")
                value = value.strip() or None
            record[field] = value
        record["missing_info"] = [field for field in EDIT_FIELDS if field != "ambiguities" and record[field] is None]
        validate_event(record, root=self.root)
        changed = any(record[field] != original[field] for field in EDIT_FIELDS)
        if changed and not notes.strip():
            raise _InputError("Explain manual corrections in review notes before confirming.")
        return record, notes.strip()

    def _review_token(self, state, document, record, notes):
        return self._sign({"purpose": "session_review", "document": document,
                           "extraction_seal": state["extraction_seal"], "reviewed_event": record, "notes": notes})

    def confirm(self, state, currentdoc, edits, notes):
        result = self.invalidate_review(state)
        try:
            document = _document(currentdoc)
            self._extraction_ok(state, document)
            record, notes = self._review(state, edits, notes)
            result.update(reviewed_event=record, review_notes=notes,
                          review_digest=self._review_token(state, document, record, notes),
                          status="review_confirmed", error=None)
        except _InputError as exc:
            result.update(status="review_failed", error=str(exc))
        except Exception:
            result.update(status="review_failed", error="Review fields failed validation; no confirmation accepted.")
        return result

    def apply(self, state, currentdoc, edits, notes, increment=3000, conversion=1):
        result = deepcopy(state) if isinstance(state, dict) else self._new()
        result["result"] = None
        try:
            document = _document(currentdoc)
            self._extraction_ok(state, document)
            if self.evaluation_only(state):
                raise _InputError(EVALUATION_ONLY_MESSAGE)
            record, notes = self._review(state, edits, notes)
            digest = self._review_token(state, document, record, notes)
            if (state.get("reviewed_event") != record
                    or not hmac.compare_digest(str(state.get("review_digest", "")), digest)):
                raise _InputError("Confirm these exact source fields, edits and notes before applying.")
            if record["city"] not in set(self._forecast.city):
                raise _InputError("Choose an explicit city in the cached forecast; no city is inferred.")
            if not record["start_date"] or not record["end_date"]:
                raise _InputError("Both event dates are required; manually supply missing facts with review notes.")
            if any(date.fromisoformat(record[key]).year != 2026 for key in ["start_date", "end_date"]):
                raise _InputError("Both event dates must be within the 2026 planning year.")
            if isinstance(conversion, bool) or conversion not in (1, 2):
                raise _InputError("Handling actions per course bike must be 1 or 2; 120 bikes/shift stays fixed.")
            if isinstance(increment, bool) or not isinstance(increment, (int, float)) or not math.isfinite(increment) or increment < 0:
                raise _InputError("Event increment must be finite and nonnegative.")
            result["result"] = self._plan(record, notes, float(increment), int(conversion))
            result.update(status="plan_ready", error=None)
        except _InputError as exc:
            result.update(reviewed_event=None, review_digest=None, review_notes="", status="apply_blocked", error=str(exc))
        except Exception:
            result.update(reviewed_event=None, review_digest=None, review_notes="", status="plan_failed",
                          error="Planning or validation failed; no new plan accepted.")
        return result

    def _plan(self, record, notes, increment, conversion):
        cfg = replace(self._cfg, affected_users_per_proxy_bike=self._cfg.affected_users_per_proxy_bike * conversion)
        forecast = self._forecast.copy(deep=True)
        actual = self._actual.copy(deep=True)
        forecast["demand_bikes"] /= conversion
        actual["demand_bikes"] /= conversion
        if conversion not in self._base_cache:
            initial, _ = baseline_plan(forecast, cfg)
            no_event, _ = plan_crews(forecast, cfg)
            self._base_cache[conversion] = (initial.copy(deep=True), no_event.copy(deep=True))
        initial, no_event = [frame.copy(deep=True) for frame in self._base_cache[conversion]]
        # event_adjustments operates in planner units, so convert the assumed
        # handling increment consistently along with the base demand.
        adjusted = event_adjustments(forecast, [record], extra_moves_per_event=increment / conversion)
        changed, solver = plan_crews(adjusted, cfg)
        group = record["city"] if record["city"] in CORE_CITIES else OTHER_POOL
        rows = []
        for name, plan in [("initial_crews", initial), ("no_event", no_event), ("reviewed_event", changed)]:
            rows.extend(_period_row(plan, actual, name, conversion, cfg))
        month_rows = []
        days = pd.date_range(record["start_date"], record["end_date"], freq="D")
        for period, count in pd.Series(days.to_period("M")).value_counts().sort_index().items():
            month_rows.append({"year": period.year, "month": period.month, "staffing_group": group,
                               "city": record["city"], "status": "included_session_review",
                               "event_name": record["event_name"], "source_url": record["source_url"],
                               "event_increment_handling_actions": increment * count / len(days)})
        ledger = pd.DataFrame(month_rows)
        chain = _chain(no_event, changed, ledger, "session_reviewed_event")
        chain = chain[chain.city == group].sort_values(["year", "month"]).reset_index(drop=True).copy()
        for suffix in ["base", "scenario"]:
            for decision in ["hires_decision", "fires_notice", "seasonal_start_decision"]:
                chain["prior_month_" + decision + "_" + suffix] = (
                    chain[decision + "_" + suffix].shift(1).fillna(0).astype(int))
        chain["hire_decision_month_for_active_month"] = [
            "No Dec2025 decision / fixed initial" if month == 1 else f"2026-{month - 1:02d}"
            for month in chain.month]
        chain["current_decisions_effective_month"] = [
            "2027-01 (outside planning horizon)" if month == 12 else f"2026-{month + 1:02d}"
            for month in chain.month]
        chain["demand_handling_actions_base"] = chain.demand_bikes_base * conversion
        chain["demand_handling_actions_scenario"] = chain.demand_bikes_scenario * conversion
        chain["capacity_handling_actions_base"] = chain.capacity_bikes_base * conversion
        chain["capacity_handling_actions_scenario"] = chain.capacity_bikes_scenario * conversion
        chain["uncovered_handling_actions_base"] = chain.unmet_bikes_base * conversion
        chain["uncovered_handling_actions_scenario"] = chain.unmet_bikes_scenario * conversion
        chain["demand_unit"] = "course-bike units; handling-action columns use declared conversion"
        return {
            # Reuse these already-computed plans for geography; no new solve or allocation.
            "geographic_plans": {"base": _clean_frame(no_event), "scenario": _clean_frame(changed)},
            "period_comparison": _clean_frame(pd.DataFrame(rows)),
            "monthly_chain": _clean_frame(chain),
            "city_month_inputs": deepcopy(month_rows),
            "summary": {"selected_city": record["city"], "selected_group": group,
                        "handling_actions_per_course_bike": conversion, "course_bikes_per_shift": 120,
                        "increment_handling_actions_per_event": increment, "review_notes": notes,
                        "human_confirmation_scope": "this UI session only; evaluation sheets unchanged",
                        "solver": solver},
            "assumptions": [
                "Uncalibrated retrospective event scenario; not proven forecast improvement.",
                "Full-time hire/firing notices and seasonal-start decisions affect next-month staffing; January is fixed initial, with no December 2025 decision.",
                "Annual forecast cost/shortfall and Jan-Sep observed-proxy cost/shortfall use matching horizons.",
                "Mandatory 2027 seasonal tail is separate; full-time continuation remains a disclosed horizon assumption.",
                "120 course bikes/shift is fixed; conversion 2 assumes paired handling endpoints, not measured productivity.",
                "Proxy shortage is not measured lost trips or customer loss; rider conversion is assumed.",
                "Shared other-city capacity is a policy exception; monthly budgets are not route schedules.",
            ],
        }
