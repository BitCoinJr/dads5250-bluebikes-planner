"""Reproduce all review tables, figures and demo text from cached real aggregates."""
from __future__ import annotations

import json
import os
import hashlib
import platform
from datetime import datetime,timezone
from dataclasses import replace,asdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .events import run_extraction,event_adjustments,check_config
from .forecast import forecast_2026,backtest_predictions,error_metrics
from .planner import PlannerConfig,plan_crews,baseline_plan,evaluate_plan,allocate_city_capacity


def _json(path, obj):
    path.write_text(json.dumps(obj,indent=2,default=str,allow_nan=False),encoding="utf-8")


def _performance(frame):
    return {"actual_proxy_bikes":float(frame.actual_demand_bikes.sum()),
            "uncovered_proxy_bikes":float(frame.actual_unmet_bikes.sum()),
            "crew_cost_in_evaluated_months":float(frame.crew_cost.sum()),
            "assumed_service_loss":float(frame.assumed_actual_service_loss.sum())}


def run_analysis(root=None, event_mode="fixture"):
    root=Path(root) if root else Path(__file__).resolve().parents[1]
    out=root/"results"; out.mkdir(exist_ok=True)
    figs=out/"figures"; figs.mkdir(exist_ok=True)
    data=pd.read_csv(root/"data/processed/monthly.csv")
    data_quality={"status":"metadata_absent"}
    diagpath=root/"data/metadata/diagnostics.json"
    if diagpath.exists():
        diag=json.loads(diagpath.read_text(encoding="utf-8"))
        records=[{"source_month":month,**{k:stats[k] for k in ["raw_rows","valid_rows","start_matched","end_matched","start_join_rate","end_join_rate","duplicate_ride_ids_removed","invalid_timestamps_or_negative_duration"]}}
                 for month,stats in sorted(diag["months"].items()) if month in diag["requested_months"]]
        qa=pd.DataFrame(records)
        qa.to_csv(out/"data_quality.csv",index=False)
        data_quality={"status":"real_archive_diagnostics","raw_trips":int(qa.raw_rows.sum()),
                      "valid_trips":int(qa.valid_rows.sum()),"invalid_rows":int(qa.invalid_timestamps_or_negative_duration.sum()),
                      "duplicate_ride_ids_removed":int(qa.duplicate_ride_ids_removed.sum()),
                      "weighted_start_join_rate":float(qa.start_matched.sum()/qa.valid_rows.sum()),
                      "weighted_end_join_rate":float(qa.end_matched.sum()/qa.valid_rows.sum()),
                      "station_snapshot_effective_date":diag["station_source"]["effective_date"],
                      "station_snapshot_checked_utc":diag["station_source"]["download_checked_utc"]}
        data_quality["cross_archive_duplicate_rows_removed"]=sum(v.get("cross_archive_duplicate_ids_removed",0) for k,v in diag["months"].items() if k in diag["requested_months"])
        data_quality["coverage_limitations"]=diag.get("coverage_limitations",[])
    forecast,validation,holdout=forecast_2026(data)
    events=run_extraction(event_mode,root)
    if event_mode in ["live","recorded"] and not events["live_llm_verified"]:
        raise RuntimeError(f"Requested API evidence unavailable: {events['status']}; no fixture fallback")
    live_check = events if event_mode in ["live","recorded"] else {
        "status":"not_requested_key_present" if check_config(root)["key_present"] else "blocked_missing_api_key",
        "api_calls":0,"live_llm_verified":False,"key_value_logged":False}
    _json(out/"live_llm_check.json",live_check)
    _json(out/"event_extraction.json",events)
    fixture_result=run_extraction("fixture",root)
    _json(out/"event_extraction_fixture.json",fixture_result)
    detail=events["evaluation"].get("details",[])
    fields=sorted({row["field"] for row in detail})
    calls=events.get("calls",[])
    evaluation_report={
        "provider":"openai","analysis_mode":event_mode,
        "live_llm_verified":events["live_llm_verified"],
        "api_calls_this_analysis":events["api_calls"],
        "original_live_api_calls":events.get("recorded_api_calls",events["api_calls"]),
        "actual_model_snapshots":sorted({call["model"] for call in calls}),
        "validated_live_records":len(events["events"]) if events["live_llm_verified"] else 0,
        "fixture_records":fixture_result["fixture_schema_valid_count"],"fixture_api_calls":0,
        "fixture_model_accuracy":None,
        "reference_status":events["evaluation"].get("reference_status","not_scored"),
        "metric":"exact agreement with frozen provisional agent references",
        "correct_fields":events["evaluation"].get("correct_fields"),
        "total_fields":events["evaluation"].get("total_fields"),
        "exact_agreement":events["evaluation"].get("accuracy"),
        "by_field":[{"field":field,"matching":sum(row["correct"] for row in detail if row["field"]==field),
                     "total":sum(row["field"]==field for row in detail)} for field in fields],
        "disagreements":[row for row in detail if not row["correct"]],
        "input_tokens":sum(call.get("usage",{}).get("input_tokens",0) for call in calls),
        "output_tokens":sum(call.get("usage",{}).get("output_tokens",0) for call in calls),
        "request_latency_seconds_sum":round(sum(call.get("latency_seconds",0) for call in calls),3),
        "reference_files_sha256":{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
                                  ["fixtures/event_documents.json","prompts/event_extraction_v1.txt","prompts/event_schema.json"]},
        "semantic_review_note":"Frozen references are AI drafts, not human-reviewed gold. Four curated cases all have null crowd; the 20 scored fields exclude ambiguity text.",
        "unscored_review_caveat":("The HOCR ambiguity about the event being known to span multiple locations goes beyond the supplied excerpt. Preserve raw output and obtain human review." if events["live_llm_verified"] else "No actual API output evaluated in fixture mode; model semantic quality is not measured."),
        "human_review_complete":False,
    }
    _json(out/"event_extraction_evaluation.json",evaluation_report)
    base_event=event_adjustments(forecast,events["events"],extra_moves_per_event=0)
    # This is an incremental stress scenario, not a fitted event prediction.
    event_scenario=event_adjustments(forecast,events["events"],extra_moves_per_event=3000)
    cfg=PlannerConfig()
    plan,ps=plan_crews(base_event,cfg)
    baseline,bs=baseline_plan(base_event,cfg)
    event_plan,es=plan_crews(event_scenario,cfg)
    delta=plan[["city","month","full_time","seasonal","capacity_bikes"]].merge(
        event_plan[["city","month","full_time","seasonal","capacity_bikes"]],on=["city","month"],suffixes=("_base","_event"))
    for col in ["full_time","seasonal","capacity_bikes"]:
        delta[f"{col}_change"]=delta[f"{col}_event"]-delta[f"{col}_base"]
    city_allocation=allocate_city_capacity(plan,base_event,cfg)
    actual=data[(data.year==2026)&data.month.between(1,9)].copy()
    expected=len(forecast.city.unique())*9
    if len(actual)!=expected:
        raise ValueError(f"Backtest incomplete: {len(actual)} city-months vs {expected}; no filling")
    keycols=["year","month","city"]
    expected_keys=pd.MultiIndex.from_frame(forecast[forecast.month<=9][keycols])
    actual_keys=pd.MultiIndex.from_frame(actual[keycols])
    if actual_keys.has_duplicates or len(expected_keys.difference(actual_keys)) or len(actual_keys.difference(expected_keys)):
        raise ValueError("Backtest city-month keys do not exactly match the forecast window")
    predicted,forecast_metrics=backtest_predictions(base_event,actual)
    jan_aug=predicted[predicted.month<=8]
    jan_aug_metrics=error_metrics(jan_aug.demand_bikes_actual,jan_aug.demand_bikes_forecast)
    pred_event,event_metrics=backtest_predictions(event_scenario,actual)
    evaluations={"initial_crews":evaluate_plan(baseline,actual,cfg),
                 "proposed":evaluate_plan(plan,actual,cfg),
                 "event_scenario":evaluate_plan(event_plan,actual,cfg)}
    eval_table=pd.DataFrame([{"plan":name,**_performance(table)} for name,table in evaluations.items()])
    # Stress the SAME plan on observed proxy demand; do not silently replan in backtest.
    sensitivity=[]
    for factor in [.8,1.,1.2]:
        stressed=actual.copy(); stressed["demand_bikes"]*=factor
        for name,staffing in [("initial_crews",baseline),("proposed",plan)]:
            result=evaluate_plan(staffing,stressed,cfg)
            sensitivity.append({"scenario":"demand", "factor":factor,"plan":name,**_performance(result)})
    # e-bike capacity effect is assumed. It is not inferred from observed trip shares.
    for capacity_factor in [.9,1.]:
        altered=replace(cfg,bikes_per_shift=cfg.bikes_per_shift*capacity_factor)
        result=evaluate_plan(plan,actual,altered)
        sensitivity.append({"scenario":"ebike_capacity_assumption","factor":capacity_factor,"plan":"proposed",**_performance(result)})
    # Unit interpretation: one completed pickup+delivery vs one handling action.
    result=evaluate_plan(plan,actual,replace(cfg,bikes_per_shift=cfg.bikes_per_shift*2))
    sensitivity.append({"scenario":"120_completed_relocations_implies_240_handling_actions","factor":2.,"plan":"proposed",**_performance(result)})
    sensitivity=pd.DataFrame(sensitivity)
    # Show how the uncertain customer conversion changes the recommended plan.
    loss_sensitivity=[]
    for multiplier in [0.,.5,1.,2.]:
        if multiplier==1.: s=ps
        else: _,s=plan_crews(base_event,replace(cfg,affected_users_per_proxy_bike=multiplier))
        loss_sensitivity.append({"assumed_users_per_uncovered_proxy_bike":multiplier,**s})
    loss_sensitivity=pd.DataFrame(loss_sensitivity)
    dedicated,dedicated_summary=plan_crews(base_event,replace(cfg,pool_other_cities=False))
    dedicated_eval=evaluate_plan(dedicated,actual,replace(cfg,pool_other_cities=False))
    outputs={"forecast_2026":forecast,"validation_2025":validation,"validation_predictions_2025":holdout,
             "plan_2026":plan,"baseline_2026":baseline,"event_scenario_plan_2026":event_plan,
             "city_capacity_allocation_2026":city_allocation,"backtest_predictions":predicted,
             "event_scenario_predictions":pred_event,"backtest_comparison":eval_table,
             "sensitivity":sensitivity,"loss_conversion_sensitivity":loss_sensitivity,
             "dedicated_city_plan_2026":dedicated,"event_plan_delta":delta}
    for name,table in {**outputs,**{f"backtest_{k}":v for k,v in evaluations.items()}}.items():
        table.to_csv(out/f"{name}.csv",index=False)
    summary={"artifact_status":"reviewable_initial_version_submission_incomplete",
             "data_periods":sorted((data.year.astype(str)+"-"+data.month.astype(str).str.zfill(2)).unique().tolist()),
             "cities":sorted(data.city.unique().tolist()),"training_years":[2024,2025],
             "data_quality":data_quality,
             "backtest_months":"2026-01 through 2026-09", "selected_model":forecast.model.iloc[0],
             "forecast_backtest":forecast_metrics,"event_scenario_backtest":event_metrics,
             "forecast_backtest_jan_aug":jan_aug_metrics,
             "backtest_boundary_note":"September 2026 end-month archive omits September departures returning in unpublished October archive. Jan-Mar 2026 are end-month partitioned but April is start-month partitioned: March-start/April-end trips may be absent from both. Counts are observed available-file proxy, not complete trip ground truth; no trips imputed. Jan-Aug comparison removes only the final right boundary, not the internal gap.",
             "event_increment_moves_per_event_assumption":3000,
             "event_comparison_status":"retrospective uncalibrated stress scenario; sources not all available in January 2026",
             "event_default_increment":0,"events_status":events["status"],
             "live_llm_verified":events["live_llm_verified"],
             "event_extraction_evaluation":evaluation_report,
             "api_calls_this_run":events["api_calls"],"recorded_api_calls":events.get("recorded_api_calls",0),
             "proposed":ps,"initial_crews":bs,"event_scenario":es,
             "dedicated_city_scenario":{**dedicated_summary,"backtest":_performance(dedicated_eval)},
             "backtest_comparison":eval_table.to_dict("records"),
             "unfinished":["TA confirmation","live LLM API evidence and human-gold evaluation" if not events["live_llm_verified"] else "human review of LLM outputs and frozen provisional reference labels",
                           "all members' review and contributions","3-minute video recording/upload","Canvas submission"]}
    _json(out/"summary.json",summary)
    _json(out/"planning_config.json",asdict(cfg))
    _figures(data,forecast,plan,evaluations,sensitivity,figs)
    _demo(summary,root)
    _json(out/"run_metadata.json",{
        "executed_utc":datetime.now(timezone.utc).isoformat(),"python":platform.python_version(),
        "event_mode":event_mode,"input_monthly_sha256":hashlib.sha256((root/"data/processed/monthly.csv").read_bytes()).hexdigest(),
        "code_sha256":{str(p.relative_to(Path(__file__).parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob("*.py"))},
        "results_sha256":{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob("*")) if p.is_file() and p.name!="run_metadata.json"},
        "note":"Real data when using committed monthly.csv; ignored build/SYNTHETIC_INTEGRATION_ONLY is a separate synthetic integration check."})
    return summary


def _figures(data,forecast,plan,evaluations,sensitivity,figs):
    plt.rcParams.update({"font.size":10,"figure.dpi":140,"savefig.bbox":"tight"})
    colors={2024:"#b5bfc9",2025:"#597c9b",2026:"#d86c32"}
    fig,ax=plt.subplots(figsize=(10,4))
    for year,g in data.groupby("year"):
        g=g.groupby("month").demand_bikes.sum()
        ax.plot(g.index,g.values,label=f"{year} observed-trip proxy",color=colors.get(year),marker="o",ms=3)
    g=forecast.groupby("month").demand_bikes.sum()
    ax.plot(g.index,g.values,"--",color="#1c5f58",label="2026 frozen forecast")
    ax.set(xlabel="Month",ylabel="Proxy bike handling tasks",xticks=range(1,13),title="Rebalancing proxy: real aggregates and frozen forecast")
    ax.legend(fontsize=8,ncol=2); ax.grid(alpha=.2)
    fig.text(.02,-.03,"Observed-file proxy: current station snapshot; March/April 2026 gap possible; September departures right-censored.",fontsize=8)
    fig.savefig(figs/"demand_forecast.png"); plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(10,6),layout="constrained")
    for ax,col,title in zip(axes,["full_time","seasonal"],["Full-time crews","Seasonal crews (system limit 8)"]):
        table=plan.pivot(index="city",columns="month",values=col)
        image=ax.imshow(table,aspect="auto",cmap="Blues",vmin=0)
        for row in range(len(table)):
            for column in range(12):
                value=int(table.iloc[row,column]); ax.text(column,row,str(value),ha="center",va="center",fontsize=9,color="white" if value>table.max().max()*.6 else "#172e42")
        ax.set(xticks=range(12),xticklabels=range(1,13),yticks=range(len(table)),yticklabels=table.index,title=title)
    fig.savefig(figs/"crew_plan.png"); plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4))
    for name,table in evaluations.items():
        g=table.groupby("month").actual_unmet_bikes.sum()
        label="retrospective event stress" if name=="event_scenario" else name.replace("_"," ")
        ax.plot(g.index,g.values,marker="o",label=label)
    ax.set(xlabel="2026 month",ylabel="Uncovered proxy tasks",xticks=range(1,10),title="Frozen plans evaluated against Jan-Sep 2026 proxy")
    ax.grid(alpha=.2); ax.legend()
    fig.text(.02,-.03,"Monthly handling-task capacity model; March/April gap possible and September departures right-censored.",fontsize=8)
    fig.savefig(figs/"backtest_shortfall.png"); plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4))
    d=sensitivity[sensitivity.scenario=="demand"]
    for name,g in d.groupby("plan"):
        ax.plot(g.factor,g.uncovered_proxy_bikes,marker="o",label=name)
    ax.set(xlabel="Observed proxy demand multiplier",ylabel="Jan-Sep uncovered proxy tasks",xticks=[.8,1,1.2],title="Demand sensitivity with staffing frozen")
    ax.legend(); ax.grid(alpha=.2); fig.savefig(figs/"demand_sensitivity.png"); plt.close(fig)


def _demo(s,root):
    b={r["plan"]:r for r in s["backtest_comparison"]}
    p=s["proposed"]; actual=b["proposed"]; initial=b["initial_crews"]
    api_sentence="We replay recorded real API extractions, with source and prompt provenance checked." if s['live_llm_verified'] else "This run uses agent-authored fixtures; no live API call has been verified."
    api_todo="" if s['live_llm_verified'] else "live API evidence, "
    score=s['event_extraction_evaluation']
    score_sentence=(f"Exact agreement with draft labels is {score['correct_fields']} of {score['total_fields']} fields; human review remains pending."
                    if s['live_llm_verified'] else "Fixture agreement is not model accuracy.")
    text=f"""# Three-minute demo script (English)

AI-generated draft; all three members must review and contribute. Numbers below are generated from `results/summary.json`, not manually typed claims. Recording and upload are **not done**. Speak only the paragraphs, not the headings or stage directions; rehearse timing to three minutes.

## 0:00-0:30 Problem and data

Bluebikes needs bikes where riders start and spare docks where they finish. Our prototype turns public trips into monthly staffing for {len(s['cities'])} municipalities. We trained on 2024 and 2025, holding out January through September 2026. Current station capacities approximate historical docks; unmatched stations remain excluded and audited.

Show `results/figures/demand_forecast.png`.

## 0:30-1:05 Event input and GenAI

Here is an official event announcement. Our prompt asks OpenAI for dates, location, city, crowd size and evidence in JSON. Structured output and local validation preserve null when crowd size is absent. {api_sentence} {score_sentence} Extracted facts remain separate from assumed demand effects.

Show Notebook event input, prompt and validated JSON.

## 1:05-1:45 Plan change

Stations start each day half full. Hourly flows estimate boundary corrections; resetting also counts as work. These are proxy handling tasks, not measured rebalancing or lost trips. The planner enforces hiring delays, severance, seasonal minimum contracts and the eight-crew cap, including mandatory 2027 costs. Compare the base table with our event stress scenario: three thousand assumed tasks per eligible event. That coefficient is uncalibrated, and later-published sources make this a retrospective scenario. Default uplift is zero to avoid double counting seasonality.

Show `results/figures/crew_plan.png` and the event plan delta table.

## 1:45-2:25 Validation and limitations

Held-out forecast WAPE is {s['forecast_backtest']['wape']:.1%}. September has missing return-boundary departures, so January-August is also reported. Initial crews leave {initial['uncovered_proxy_bikes']:,.0f} proxy tasks uncovered; our frozen plan leaves {actual['uncovered_proxy_bikes']:,.0f}. Annual crew cost plus committed seasonal tail is ${p['total_committed_crew_cost']:,.0f}. Assumed customer losses stay separate. We stress demand by twenty percent and test an assumed e-bike capacity penalty. Event-scenario WAPE is {s['event_scenario_backtest']['wape']:.1%}, reported whether better or worse.

Show backtest and sensitivity figures.

## 2:25-3:00 Architecture and strength

The notebook connects small Python modules for data, inventory, forecasting, extraction and optimization. Figures and this script share the same results. Our strength is traceability with hand-checkable tests. Capacity units and shared-city crews require review; dedicated-city results are also available. Before submission we still need TA confirmation, {api_todo}all-member review, and the recorded, uploaded demo.

Show `docs/architecture.md`. Do not describe the submission as complete until the video link and required reviews exist.
"""
    (root/"docs/DEMO_SCRIPT.md").write_text(text,encoding="utf-8")
