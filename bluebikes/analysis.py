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

from .events import run_extraction,event_adjustments,check_config,load_documents
from .forecast import forecast_2026,backtest_predictions,error_metrics
from .scenarios import generate_review_scenarios
from .unit_examples import build_unit_examples
from .geography import geographic_result_from_chain, load_stations, render_geography
from .event_validation import run_additional_evaluation
from .review_tables import write_review_csv
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
    # The course's 120 is unchanged: convert input actions to course-bike units.
    course_actual=actual.copy(); course_actual["demand_bikes"]/=2
    result=evaluate_plan(plan,course_actual,replace(cfg,affected_users_per_proxy_bike=cfg.affected_users_per_proxy_bike*2))
    for col in ["actual_demand_bikes","actual_unmet_bikes","actual_served_bikes"]:
        result[col]*=2  # report comparable handling actions, not mixed units
    sensitivity.append({"scenario":"fixed_crews_unit_conversion_2_actions_per_course_bike","factor":2.,"plan":"proposed",**_performance(result)})
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
    reviews=generate_review_scenarios(forecast,events,actual,baseline,plan,cfg)
    for name,table in reviews["tables"].items():
        table.to_csv(out/f"{name}.csv",index=False)
    _json(out/"review_scenario_assumptions.json",reviews["metadata"])
    periods=reviews["tables"]["scenario_period_comparison"]
    unit_comparison=periods[periods.scenario.isin(["proposal_no_event_factor1","replanned_no_event_factor2","initial_crews_factor1","initial_crews_factor2"])].copy()
    unit_comparison.to_csv(out/"unit_interpretation_comparison.csv",index=False)
    examples=build_unit_examples()
    for name,table in examples.items():
        if isinstance(table,pd.DataFrame): table.to_csv(out/f"unit_example_{name}.csv",index=False)
    _json(out/"unit_example_assumptions.json",{k:v for k,v in examples.items() if not isinstance(v,pd.DataFrame)})
    supplemental=(run_additional_evaluation(mode="recorded",root=root) if event_mode!="fixture" else
                  {"status":"not_loaded_in_fixture_mode","api_calls":0,"recorded_api_calls":0,"evaluation":None})
    original_documents={doc["id"]:doc for doc in load_documents(root)}
    review_rows=[]
    for detail in events["evaluation"].get("details",[]):
        doc=original_documents[detail["source_id"]]
        review_rows.append({"evaluation_batch":"original_four_frozen","source_id":doc["id"],"source_url":doc["source_url"],
                            "input_excerpt":doc["source_text"],"field":detail["field"],
                            "provisional_reference":json.dumps(detail["expected"],ensure_ascii=False),
                            "actual_llm_output":json.dumps(detail["predicted"],ensure_ascii=False),
                            "automatic_exact_match":detail["correct"],"human_judgment":"","reviewer":"","notes":"","human_review_status":"PENDING"})
    write_review_csv(out/"event_original_four_human_review.csv",review_rows)
    april=reviews["tables"]["focused_event_chain"]
    april=april[(april.city=="Boston")&(april.month==4)]
    demo_context={"status":reviews["metadata"]["event_scenario_status"],"handling_increment_per_event":3000,
                  "focused_event_april_boston":json.loads(april.to_json(orient="records")),
                  "same_period_comparisons":json.loads(periods.to_json(orient="records")),
                  "unit_replanning_comparisons":json.loads(unit_comparison.to_json(orient="records")),
                  "course_bikes_per_shift_fixed":120,"human_review_complete":False}
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
             "demo_context":demo_context,
             "additional_event_evaluation":supplemental.get("evaluation"),
             "additional_event_evaluation_status":supplemental["status"],
             "additional_recorded_api_calls":supplemental.get("recorded_api_calls",supplemental.get("api_calls",0)),
             "api_calls_this_run":events["api_calls"],"recorded_api_calls":events.get("recorded_api_calls",0),
             "proposed":ps,"initial_crews":bs,"event_scenario":es,
             "dedicated_city_scenario":{**dedicated_summary,"backtest":_performance(dedicated_eval)},
             "backtest_comparison":eval_table.to_dict("records"),
             "unfinished":["TA confirmation","live LLM API evidence and human-gold evaluation" if not events["live_llm_verified"] else "human review of LLM outputs and frozen provisional reference labels",
                           "all members' review and contributions","3-minute video recording/upload","Canvas submission"]}
    _json(out/"summary.json",summary)
    _json(out/"planning_config.json",asdict(cfg))
    _figures(data,forecast,plan,evaluations,sensitivity,figs)
    _review_figures(reviews["tables"],examples,figs,events["live_llm_verified"])
    geographic = render_geography(
        geographic_result_from_chain(reviews["tables"]["focused_event_chain"]), 4, load_stations(root))
    if geographic["figure"] is None:
        raise ValueError("The cached focused scenario or station coordinates cannot be visualized")
    geographic["figure"].savefig(figs/"geographic_crew_comparison.png", dpi=150)
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


def _review_figures(tables,examples,figs,live_verified):
    from matplotlib.patches import FancyBboxPatch
    row=tables["focused_event_chain"].query("city == 'Boston' and month == 4").iloc[0]
    # Literal currency signs and fixed-width boxes prevent mathtext and overlap.
    with plt.rc_context({"text.parse_math":False}):
        fig,ax=plt.subplots(figsize=(16,4.2)); ax.axis("off")
        labels=["Real event text\nBoston Marathon\n20 April 2026",
                ("Recorded real OpenAI" if live_verified else "Agent fixture contract")+"\ncity: Boston\ndate: 2026-04-20",
                "Uncalibrated assumption\n+3,000 handling actions\nBoston / April",
                f"Frozen forecast + increment\n{row.demand_bikes_base:,.0f} -> {row.demand_bikes_scenario:,.0f}\nhandling actions",
                f"Conditional April plan\nFT {int(row.full_time_base)} -> {int(row.full_time_scenario)}\nBoston crew cash cost\n${row.crew_cost_base:,.0f} -> ${row.crew_cost_scenario:,.0f}"]
        for i,label in enumerate(labels):
            x=.012+i*.2
            ax.add_patch(FancyBboxPatch((x,.32),.173,.40,boxstyle="round,pad=0.008",transform=ax.transAxes,facecolor="#e8f1f4",edgecolor="#336577"))
            ax.text(x+.0865,.52,label,transform=ax.transAxes,ha="center",va="center",fontsize=10)
            if i<4:
                ax.annotate("",xy=(x+.191,.52),xytext=(x+.182,.52),xycoords="axes fraction",arrowprops=dict(arrowstyle="->",color="#336577",lw=2))
        ax.set_title("Event-to-plan demo: focused retrospective scenario",fontsize=16,pad=14)
        fig.text(.07,.085,"+3,000 is separate from extracted facts; no demonstrated forecast improvement.\nBoston uses the named route-endpoint convention. Annual contract decisions can change other months.",fontsize=10)
        fig.savefig(figs/"event_demo_chain.png");plt.close(fig)
        fig,ax=plt.subplots(figsize=(11,4.4));ax.axis("off")
        stations=[(.23,"Station A: 2 bikes / 4 docks\n4 departures\n2 boundary supply + 2 reset supply"),
                  (.77,"Station B: 2 bikes / 4 docks\n4 arrivals\n2 boundary collection + 2 reset collection")]
        for x,label in stations:
            ax.text(x,.68,label,transform=ax.transAxes,ha="center",va="center",fontsize=11,
                    bbox=dict(boxstyle="round,pad=.65",facecolor="#e8f1f4",edgecolor="#336577"))
        ax.annotate("",xy=(.27,.37),xytext=(.73,.37),xycoords="axes fraction",arrowprops=dict(arrowstyle="->",lw=2,color="#336577"))
        ax.text(.5,.20,"Assumed pairing: 4 relocation tasks = 8 station handling actions",transform=ax.transAxes,ha="center",va="center",fontsize=11)
        ax.set_title("Synthetic hand count: the course's 120 bikes/shift stays fixed",fontsize=14,pad=15)
        fig.text(.065,.025,"Pairing is an algebraic scenario, not a proven van route.\nUnbalanced station/depot actions cannot automatically be divided by two.",fontsize=10)
        fig.savefig(figs/"handling_unit_demo.png");plt.close(fig)


def _demo(s, root):
    """Render narration from saved results only; never invoke analysis or the API."""
    focused = s["demo_context"]["focused_event_april_boston"][0]
    from .human_review import load_reviews
    human_line = ("Satoshi reviewed seven cases and conditionally accepted eight disclosed assumptions."
                  if load_reviews(root)["record"] else
                  "Human adjudication and member contributions remain unconfirmed.")
    text = f"""# Three-minute screen demonstration

AI-assisted English narration for the current local app. **Recording and a spoken end-to-end rehearsal are not complete.** Target final video: **2:45–2:55**, including clicks and waits; three minutes is the limit. Timecodes below are provisional pacing guides, not measured delivery. Read only the six narration paragraphs between the markers. Follow the matching [recording run sheet](RECORDING_RUNSHEET.md); [overlay timecodes](recording_overlays.srt) must be synchronized after recording.

The app uses a **saved response from a real OpenAI API call**, not a new call, fixture or mock. No fabricated loading sequence. Launch a fresh local server on an unused port (recommended 7881), as explained in the run sheet. Begin with the original Marathon, 3,000 handling actions and conversion 1, **not confirmed and not applied**.

## 0:00–0:22 A · Bluebikes and the decision

<!-- NARRATION_START -->
Bluebikes is Greater Boston’s bike-share system. Rebalancing moves bikes from surplus stations to stations running short. We plan monthly full-time and seasonal crews for 2026, including hiring dates and contract starts. A crew means a driver and van. Baseline means modeled staffing, not actual deployment.
<!-- NARRATION_END -->

## 0:22–0:48 B · AI and analytics

<!-- NARRATION_START -->
Python uses 2024–2025 trips to estimate workload and plan crews. January–September 2026 trips are held out for backtesting. API calls obtain OpenAI responses. Prompt engineering defines which event facts to extract. Structured output gives validated fields for human review; unknowns should stay unknown. People supply demand assumptions; Python calculates the plan.
<!-- NARRATION_END -->

## 0:48–1:23 C · Saved Marathon facts

<!-- NARRATION_START -->
This demo uses a saved response from a real OpenAI API call. There is no new call now. Here is the original Marathon excerpt beside its extraction. April twentieth is stated. Boston is the route endpoint, not the whole event area. Thirty thousand refers to athletes. Spectators remain unknown. Evidence and human annotations stay visible.
<!-- NARRATION_END -->

## 1:23–2:05 D · Confirm, Apply and the decision

<!-- NARRATION_START -->
I confirm the reviewed facts, then explicitly apply {focused['event_increment_handling_actions']:,.0f} added handling actions. This is an uncalibrated retrospective scenario, not OpenAI’s demand prediction or a measured event effect. Boston’s April full-time crews change from {int(focused['full_time_base'])} to {int(focused['full_time_scenario'])}. Monthly crew cash cost rises from ${focused['crew_cost_base']:,.0f} to ${focused['crew_cost_scenario']:,.0f}. The hiring decision is in March. This is April’s cost, not an annual total. Our base conversion assumes one handling action per course bike; 120 bikes per shift stays fixed.
<!-- NARRATION_END -->

## 2:05–2:20 E · Geographic comparison

<!-- NARRATION_START -->
Both geographic panels show April. Dots mark stations; bubbles compare modeled city crews, not bases or routes. Nine other cities share one pool, shown separately.
<!-- NARRATION_END -->

## 2:20–2:55 F · Evaluation, contribution and close

<!-- NARRATION_START -->
Review found unsupported dates and participants mistaken for spectators. The three supplemental cases are evaluation only and cannot enter plans. Our strongest feature preserves failures while connecting text to staffing and hiring decisions. {human_line} Other members’ contributions remain unconfirmed. Uncovered proxy work is not measured lost trips.
<!-- NARRATION_END -->

## Timing and pronunciation (not spoken)

The six paragraphs contain **307 whitespace-delimited words**. Expanding numeric years, ranges, costs and quantities as below gives **322 spoken-word equivalents**; abbreviations such as API still count as one token, so this is an estimate, not an audio measurement.

- Read 2024–2025 as “twenty twenty-four and twenty twenty-five”; January–September as “January through September”; 2026 as “twenty twenty-six”.
- Read 3,000 as “three thousand”; $72,000/$78,000 as “seventy-two/seventy-eight thousand dollars”; 120 as “one hundred twenty”; 12/13 as “twelve/thirteen”.
- At **120 expanded words/minute**, narration is about **161 seconds**. Allow **10–14 seconds of pauses not already covered by speech**: about **171–175 seconds**. At 110 words/minute plus ten seconds, about **186 seconds**, which exceeds the limit.
- The operator can scroll/click while the narrator speaks. Do not add the entire operation-only run duration to speech time; do not subtract it either and call the result measured. The actual combined take must be timed.
- Operation-only measurements, narration estimates and unmeasured spoken rehearsal are recorded separately in [the run sheet](RECORDING_RUNSHEET.md). The first two do not prove a sub-three-minute video.

If the full take overruns, cut these exact optional sentences, then measure again: “There is no new call now.” (6 words); “Evidence and human annotations stay visible.” (6); “This is April’s cost, not an annual total.” (8). Keep the saved-real-response disclosure, human gate, +3,000 assumption, April cost label, March hiring, shared pool and review failures. Do not solve an overrun by reading faster than clearly understandable.

## Evidence and contribution boundaries (not spoken)

The original **19/20** and supplemental **11/15** are frozen agreement counts against reference labels, not general human-reviewed accuracy. They need not be spoken in this short video. Preserve unsupported-date and participant/spectator failures; all three supplemental cases remain excluded from plans even after editing and session confirmation.

Satoshi's seven event adjudications and conditional acceptance of eight disclosed model topics are supported by [the human record](human_review_decisions.json). Do not infer code authorship, empirical validation, TA approval or other members' work. Vinay and Aditi's contribution evidence and narrator/operator assignments are still pending. Membership and invitations are not contribution.

The map uses station coordinates and city means, not actual crew bases, routes or geocoded event locations. Keep both April panels at the same extent/scale and the nine-city shared pool visible. Do not open annual-cost tabs during the April cash-cost explanation.

Numerical narration is generated from the saved focused result by the existing `bluebikes.analysis._demo` function. Regeneration must preserve this script. The Mermaid editing source remains `docs/diagrams/bluebikes_flow.mmd`. No new API request, full computation, recording, upload, external contact or submission is part of this preparation.
"""
    (root / "docs/DEMO_SCRIPT.md").write_text(text, encoding="utf-8")
