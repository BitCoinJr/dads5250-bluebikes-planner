"""Review scenarios: real-event wiring, matched horizons, and explicit units.

No API calls or model fitting occur here. All replanning consumes the supplied
frozen training forecast; actual 2026 proxy data is used only for evaluation.
"""
from __future__ import annotations

from dataclasses import replace
import json
import math

import pandas as pd

from .events import event_adjustments, validate_event
from .planner import (
    CORE_CITIES, OTHER_POOL, PlannerConfig, allocate_city_capacity,
    baseline_plan, evaluate_plan, plan_crews,
)

KEYS = ["year", "month", "city"]
EVENT_INCREMENT = 3000.0


def _group(city, cfg):
    return city if not cfg.pool_other_cities or city in CORE_CITIES else OTHER_POOL


def _events_ledger(forecast, events, cfg):
    """Retain excluded/ambiguous inputs as well as eligible event-month rows."""
    rows, seen = [], set()
    keys = set(forecast[KEYS].itertuples(index=False, name=None))
    for event in events:
        validate_event(event)
        facts = {
            "event_name": event["event_name"], "start_date": event["start_date"],
            "end_date": event["end_date"], "city": event["city"],
            "source_url": event["source_url"], "evidence_text": event["evidence_text"],
            "expected_crowd_size": event["expected_crowd_size"],
            "ambiguities": json.dumps(event["ambiguities"], ensure_ascii=False),
            "increment_assumption_handling_actions_per_event": EVENT_INCREMENT,
        }
        identity = (event["source_url"], event["event_name"], event["start_date"], event["end_date"])
        reason = None
        if identity in seen:
            reason = "excluded_duplicate_event"
        seen.add(identity)
        if reason is None and not event["start_date"]:
            reason = "excluded_missing_date"
        if reason is None and not event["city"]:
            reason = "excluded_missing_city_no_location_inference"
        if reason:
            rows.append({**facts, "year": None, "month": None, "staffing_group": None,
                         "status": reason, "event_increment_handling_actions": 0.0})
            continue
        days = pd.date_range(event["start_date"], event["end_date"] or event["start_date"], freq="D")
        for period, count in pd.Series(days.to_period("M")).value_counts().sort_index().items():
            eligible = (period.year, period.month, event["city"]) in keys
            rows.append({**facts, "year": period.year, "month": period.month,
                         "staffing_group": _group(event["city"], cfg),
                         "status": ("included_with_ambiguity_review" if event["ambiguities"] else "included")
                                   if eligible else "excluded_outside_forecast_city_month",
                         "event_increment_handling_actions": EVENT_INCREMENT * count / len(days) if eligible else 0.0})
    return pd.DataFrame(rows)


def _chain(base, changed, ledger, name):
    measures = ["demand_bikes", "full_time", "seasonal", "capacity_bikes",
                "unmet_bikes", "crew_cost", "terminal_seasonal_cost",
                "hires_decision", "fires_notice", "seasonal_start_decision"]
    result = base[KEYS + measures].merge(changed[KEYS + measures], on=KEYS, validate="one_to_one",
                                       suffixes=("_base", "_scenario"))
    for measure in measures:
        result[measure + "_change"] = result[measure + "_scenario"] - result[measure + "_base"]
    included = ledger[ledger.status.str.startswith("included")].copy() if len(ledger) else ledger
    if len(included):
        facts = included.groupby(["year", "month", "staffing_group"], as_index=False).agg(
            event_increment_handling_actions=("event_increment_handling_actions", "sum"),
            event_names=("event_name", lambda values: " | ".join(values)),
            source_urls=("source_url", lambda values: " | ".join(values)),
        ).rename(columns={"staffing_group": "city"})
        result = result.merge(facts, on=KEYS, how="left", validate="one_to_one")
    else:
        result["event_increment_handling_actions"] = 0.0
        result["event_names"] = ""
        result["source_urls"] = ""
    result["event_increment_handling_actions"] = result.event_increment_handling_actions.fillna(0.0)
    for column in ["event_names", "source_urls"]:
        result[column] = result[column].fillna("")
    result["scenario"] = name
    result["demand_unit"] = "handling_actions (factor-one course-unit interpretation)"
    result["status"] = "uncalibrated retrospective scenario; not proven forecast improvement"
    # Payroll can propagate to non-event months via hiring/contract constraints.
    result["has_event_input"] = result.event_increment_handling_actions > 0
    result["has_staffing_or_cost_change"] = (
        result.full_time_change.ne(0) | result.seasonal_change.ne(0) | result.crew_cost_change.abs().gt(1e-6))
    return result.sort_values(KEYS).reset_index(drop=True)


def _period_row(plan, actual, name, factor, cfg):
    """Two rows with matched cost/service periods; tail never mixed into payroll."""
    annual_monthly = plan.groupby("month")[["full_time", "seasonal"]].sum()
    annual = {
        "scenario": name, "handling_actions_per_course_bike": factor,
        "period": "2026-01 through 2026-12", "period_months": 12,
        "demand_basis": "frozen training forecast plus declared event increment only",
        "demand_course_bike_units": float(plan.demand_bikes.sum()),
        "demand_handling_actions": float(plan.demand_bikes.sum() * factor),
        "uncovered_course_bike_units": float(plan.unmet_bikes.sum()),
        "uncovered_handling_actions": float(plan.unmet_bikes.sum() * factor),
        "crew_cash_cost_in_period": float(plan.crew_cost.sum()),
        "mandatory_seasonal_tail_cost_2027_separate": float(plan.terminal_seasonal_cost.sum()),
        "assumed_users_per_uncovered_handling_action": cfg.affected_users_per_proxy_bike / factor,
        "assumed_service_loss_in_period": float(plan.assumed_service_loss.sum()),
        "full_time_crew_months_in_period": int(plan.full_time.sum()),
        "seasonal_crew_months_in_period": int(plan.seasonal.sum()),
        "peak_full_time_crews_in_period": int(annual_monthly.full_time.max()),
        "peak_seasonal_crews_in_period": int(annual_monthly.seasonal.max()),
        "peak_total_crews_in_period": int(annual_monthly.sum(axis=1).max()),
        "ending_full_time_crews_in_period": int(annual_monthly.full_time.iloc[-1]),
        "course_bikes_per_shift": cfg.bikes_per_shift,
    }
    scored = evaluate_plan(plan, actual, cfg)
    observed_monthly = scored.groupby("month")[["full_time", "seasonal"]].sum()
    observed = {
        **annual, "period": "2026-01 through 2026-09", "period_months": 9,
        "demand_basis": "observed-trip inventory proxy; fixed forecast plan, not refitted",
        "demand_course_bike_units": float(scored.actual_demand_bikes.sum()),
        "demand_handling_actions": float(scored.actual_demand_bikes.sum() * factor),
        "uncovered_course_bike_units": float(scored.actual_unmet_bikes.sum()),
        "uncovered_handling_actions": float(scored.actual_unmet_bikes.sum() * factor),
        "crew_cash_cost_in_period": float(scored.crew_cost.sum()),
        "mandatory_seasonal_tail_cost_2027_separate": None,
        "assumed_service_loss_in_period": float(scored.assumed_actual_service_loss.sum()),
        "full_time_crew_months_in_period": int(scored.full_time.sum()),
        "seasonal_crew_months_in_period": int(scored.seasonal.sum()),
        "peak_full_time_crews_in_period": int(observed_monthly.full_time.max()),
        "peak_seasonal_crews_in_period": int(observed_monthly.seasonal.max()),
        "peak_total_crews_in_period": int(observed_monthly.sum(axis=1).max()),
        "ending_full_time_crews_in_period": int(observed_monthly.full_time.iloc[-1]),
    }
    return [annual, observed]


def _course_input(handling_demand, factor):
    result = handling_demand.copy()
    result["demand_bikes"] = result.demand_bikes / factor
    return result


def _check_inputs(forecast, actual, cfg):
    if not math.isclose(cfg.bikes_per_shift, 120.0):
        raise ValueError("Course capacity must remain 120 bikes/shift; use explicit demand-unit conversion")
    keys = pd.MultiIndex.from_frame(forecast[KEYS])
    if keys.has_duplicates or set(forecast.year) != {2026} or set(forecast.month) != set(range(1, 13)):
        raise ValueError("Need one frozen forecast per city for all twelve 2026 months")
    wanted = pd.MultiIndex.from_frame(forecast[forecast.month <= 9][KEYS])
    observed = pd.MultiIndex.from_frame(actual[KEYS])
    if observed.has_duplicates or len(wanted.difference(observed)) or len(observed.difference(wanted)):
        raise ValueError("Actual input must exactly cover the forecast cities in January-September 2026")


def generate_review_scenarios(forecast, recorded_events, actual, baseline_plan_df,
                              proposal_plan_df, config=None):
    """Return {'tables': {name: DataFrame}, 'metadata': dict} without file writes.

    recorded_events accepts the verified recorded artifact or its event list.
    The artifact is preferable: the list alone cannot establish live provenance.
    Factor two converts handling actions to course-bike units before replanning;
    120 course bikes/shift stays fixed. The assumed loss per uncovered handling
    action stays fixed by multiplying the per-course-unit penalty by the factor.
    """
    cfg = config or PlannerConfig()
    _check_inputs(forecast, actual, cfg)
    artifact = recorded_events if isinstance(recorded_events, dict) else {}
    events = artifact.get("events", []) if artifact else list(recorded_events)
    ledger = _events_ledger(forecast, events, cfg)
    # Use the single real extracted Marathon event; never invent a replacement.
    focused = [event for event in events if event.get("city") == "Boston"
               and event.get("start_date") == "2026-04-20"
               and "marathon" in event.get("event_name", "").lower()][:1]
    focused_ledger = _events_ledger(forecast, focused, cfg)
    focused_demand = event_adjustments(forecast, focused, extra_moves_per_event=EVENT_INCREMENT)
    calendar_demand = event_adjustments(forecast, events, extra_moves_per_event=EVENT_INCREMENT)
    focused_plan, focused_summary = plan_crews(focused_demand, cfg)
    calendar_plan, calendar_summary = plan_crews(calendar_demand, cfg)
    # Factor one is the caller's existing, frozen proposal. Factor two is rerun.
    factor = 2.0
    cfg_two = replace(cfg, affected_users_per_proxy_bike=cfg.affected_users_per_proxy_bike * factor)
    course_forecast_two = _course_input(forecast, factor)
    course_actual_two = _course_input(actual, factor)
    plan_two, summary_two = plan_crews(course_forecast_two, cfg_two)
    baseline_two, baseline_summary_two = baseline_plan(course_forecast_two, cfg_two)
    specifications = [
        ("initial_crews_factor1", baseline_plan_df, actual, 1.0, cfg),
        ("proposal_no_event_factor1", proposal_plan_df, actual, 1.0, cfg),
        ("focused_marathon_plus3000_factor1", focused_plan, actual, 1.0, cfg),
        ("calendar_plus3000_factor1", calendar_plan, actual, 1.0, cfg),
        ("initial_crews_factor2", baseline_two, course_actual_two, factor, cfg_two),
        ("replanned_no_event_factor2", plan_two, course_actual_two, factor, cfg_two),
    ]
    period_rows = []
    for name, plan, observed, conversion, case_cfg in specifications:
        period_rows.extend(_period_row(plan, observed, name, conversion, case_cfg))
    unit_group, unit_city = [], []
    for conversion, plan, demand, case_cfg, name in [
        (1.0, proposal_plan_df, forecast, cfg, "proposal_no_event_factor1"),
        (factor, plan_two, course_forecast_two, cfg_two, "replanned_no_event_factor2"),
    ]:
        group = plan.copy()
        group["scenario"] = name
        group["handling_actions_per_course_bike"] = conversion
        group["course_bikes_per_shift"] = 120.0
        group["demand_course_bike_units"] = group.demand_bikes
        group["demand_handling_actions"] = group.demand_bikes * conversion
        group["capacity_course_bike_units"] = group.capacity_bikes
        group["capacity_handling_actions"] = group.capacity_bikes * conversion
        group["uncovered_handling_actions"] = group.unmet_bikes * conversion
        group["assumed_users_per_uncovered_handling_action"] = cfg.affected_users_per_proxy_bike
        unit_group.append(group)
        city = allocate_city_capacity(plan, demand, case_cfg)
        city["scenario"] = name
        city["handling_actions_per_course_bike"] = conversion
        city["course_bikes_per_shift"] = 120.0
        city["demand_course_bike_units"] = city.demand_bikes
        city["demand_handling_actions"] = city.demand_bikes * conversion
        city["allocated_capacity_course_bike_units"] = city.allocated_capacity_bikes
        city["allocated_capacity_handling_actions"] = city.allocated_capacity_bikes * conversion
        unit_city.append(city)
    metadata = {
        "event_scenario_status": "uncalibrated retrospective stress; not evidence of forecast improvement",
        "increment_handling_actions_per_eligible_event": EVENT_INCREMENT,
        "recorded_event_provenance": {
            "live_llm_verified": bool(artifact.get("live_llm_verified", False)),
            "mode": artifact.get("mode", "provided_event_list_without_provenance"),
            "actual_models": sorted({call["model"] for call in artifact.get("calls", [])}),
            "api_calls_made_by_scenarios": 0,
            "human_review_complete": False,
        },
        "focused_event_found": bool(focused),
        "focused_event_source_urls": [event["source_url"] for event in focused],
        "excluded_events": (ledger[~ledger.status.str.startswith("included")].astype(object)
                            .where(pd.notna(ledger[~ledger.status.str.startswith("included")]), None)
                            .to_dict("records")) if len(ledger) else [],
        "solver_summaries": {"focused_event": focused_summary, "full_calendar": calendar_summary,
                             "unit_factor2_replanned": summary_two, "unit_factor2_baseline": baseline_summary_two},
        "course_bikes_per_shift_fixed": 120,
        "unit_conversion_factors_handling_actions_per_course_bike": [1, 2],
        "assumed_users_per_uncovered_handling_action_held_fixed": cfg.affected_users_per_proxy_bike,
        "unit_interpretation_status": "conditional counting convention, not empirical capacity evidence or resolved course interpretation",
        "unit_objective_conversion": "course unmet * conversion factor * assumed users per handling action * $5.70; payroll unchanged",
        "unit_replanning_note": "Factor two is newly optimized on converted training forecast. Earlier frozen-plan factor-two sensitivity changes capacity/service only and cannot estimate crew/cost changes.",
        "annual_period_note": "2026 Jan-Dec crew cash cost matched to forecast-proxy shortfall; mandatory 2027 seasonal tail reported separately.",
        "backtest_period_note": "2026 Jan-Sep crew cash cost matched to observed-proxy shortfall; all staffing frozen before actual evaluation. No annual cost mixed into nine-month service comparison.",
        "shared_city_note": "Integer crews belong to staffing groups. All-city fractions allocate shared capacity and payroll, not dedicated fractional crews.",
    }
    return {"tables": {
        "event_city_month_inputs": ledger,
        "event_exclusions": ledger[~ledger.status.str.startswith("included")].copy() if len(ledger) else ledger.copy(),
        "focused_event_city_month_inputs": focused_ledger,
        "focused_event_chain": _chain(proposal_plan_df, focused_plan, focused_ledger, "focused_marathon_plus3000_factor1"),
        "calendar_event_chain": _chain(proposal_plan_df, calendar_plan, ledger, "calendar_plus3000_factor1"),
        "scenario_period_comparison": pd.DataFrame(period_rows),
        "unit_group_month_comparison": pd.concat(unit_group, ignore_index=True),
        "unit_city_month_allocations": pd.concat(unit_city, ignore_index=True),
    }, "metadata": metadata}
