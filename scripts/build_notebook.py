"""Build and optionally execute the complete submission Notebook top to bottom."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import nbformat as nbf
from nbclient import NotebookClient

ROOT=Path(__file__).resolve().parents[1]


def build(event_mode='recorded'):
    cells=[]
    md=lambda text:cells.append(nbf.v4.new_markdown_cell(text))
    code=lambda text:cells.append(nbf.v4.new_code_cell(text))
    md("""# Bluebikes monthly rebalancing crew planner for 2026

**DADS5250 Generative AI in Practice — Group 8**  
Satoshi Nakamura / Vinay Manikandan Nagarajan / Aditi Rao

**Reviewable initial version; submission is incomplete.** Initial code, prose, figures and draft event annotations were AI-assisted. All members' contribution and review are pending and are not implied by the member list. TA confirmation is **not received** as of 26 October 2026. The user directed work despite the TA's reported instruction to wait; this is not approval from the TA.

User-supplied deadline: **28 October 2026, 23:59 ET = 29 October 2026, 12:59 JST**. The older Canvas 25 October display is reported outdated. No contact with the TA or members and no Canvas submission was automated.

Demo video URL: **NOT RECORDED OR UPLOADED — required before submission.**

This notebook reruns the analysis from small, committed **real-data aggregates**. Full raw-data acquisition is a separate reproducible command because the monthly trip files are large. Synthetic data appears only in explicitly labelled hand-count tests. Runtime API status is reported below; the draft reference annotations still require actual human review.
""")
    code("""from pathlib import Path
import sys, json, subprocess
import pandas as pd
from IPython.display import display, Image, Markdown
ROOT = Path.cwd()
if not (ROOT / 'bluebikes').exists():
    ROOT = ROOT.parent
assert (ROOT / 'bluebikes').exists(), 'Run with repository root as working directory'
sys.path.insert(0, str(ROOT))
pd.set_option('display.max_rows', 200)
pd.set_option('display.max_columns', 18)
from bluebikes.analysis import run_analysis
EVENT_MODE = '__EVENT_MODE__'
summary = run_analysis(ROOT, event_mode=EVENT_MODE)
print('Analysis executed using real monthly aggregates; API mode =', EVENT_MODE)
print(json.dumps({k:summary[k] for k in ['artifact_status','selected_model','live_llm_verified']}, indent=2))""".replace('__EVENT_MODE__',event_mode))
    md("""## Data and reproducibility

Sources: [Bluebikes System Data](https://bluebikes.com/system-data), [official trip bucket](https://s3.amazonaws.com/hubway-data/index.html), and the station CSV linked by the System Data page. Per-file URLs, sizes, hashes, schemas, duplicate counts, time ranges and joins are saved in `data/metadata/`. The course brief was read without changing it; its SHA256 is recorded in `docs/reference_manifest.json`.

The pipeline first processed January 2024 for Boston and Cambridge, then expanded to 2024-2025 and January-September 2026 for all municipalities in the station list. It reads monthly files in 100,000-row chunks and aggregates immediately to station-hour. Extensions are discovered from the bucket, including `.csv.zip` and the plain September 2026 CSV.

Station IDs are read as strings. The actual station file contains historic IDs and a placeholder for newer stations, while modern trip IDs use another system. The implemented join therefore uses unique, normalized **exact station names**, without fuzzy guesses. Unmatched endpoints remain excluded and audited. Current Municipality/docks are applied retrospectively; station openings, closures, renamed stations and capacity changes are not reconstructed. Zero matched activity is not proof a city historically had zero underlying demand.

Trip timestamps are assumed to be Boston local wall time. Departures use `started_at` and returns use `ended_at`, including cross-month returns. Repeated DST hours are combined; within-hour order is unavailable. December 2023 contributes January 2024 boundary returns. Archive partitioning changes from start-month to end-month during 2024 and changes again around April 2026. Repeated ride IDs across May/June 2024 and April/May 2026 are audited and corrected before the final proxy. A reverse partition switch from end-month March to start-month April 2026 can leave **March-start/April-end trips missing from both files**, an unquantified internal gap. Non-null ride IDs are also deduplicated across chunks within each archive. Invalid timestamps or negative durations are excluded and counted. **September 2026 is right-censored:** September departures returning in an unpublished October archive are absent. No missing trips are invented; January-August metrics remove only the final boundary, not the possible internal gap.
""")
    code("""data = pd.read_csv(ROOT / 'data/processed/monthly.csv')
diagnostics = json.loads((ROOT / 'data/metadata/diagnostics.json').read_text())
assert diagnostics['all_requested_months_observed'], diagnostics['missing']
assert len(data) == 33 * data.city.nunique()
print(f"Real valid trips in requested archives: {diagnostics['real_valid_trips_in_requested_archives']:,}")
print(f"Coverage: {len(diagnostics['observed_months'])} months; {data.city.nunique()} cities; {len(data)} city-months")
display(pd.DataFrame([diagnostics['station_source']]).drop(columns=['cities']))
display(data.groupby('year').agg(months=('month','nunique'), cities=('city','nunique'), departures=('departures','sum'), arrivals=('arrivals','sum')))
joins = pd.DataFrame([{'month':k, 'raw_rows':v['raw_rows'], 'valid_rows':v['valid_rows'], 'start_join_rate':v['start_join_rate'], 'end_join_rate':v['end_join_rate'], 'duplicates_removed':v['duplicate_ride_ids_removed'], 'invalid_rows':v['invalid_timestamps_or_negative_duration']} for k,v in sorted(diagnostics['months'].items()) if k in diagnostics['requested_months']])
display(joins)
print('Pilot status:', diagnostics['pilot'])
display(pd.read_csv(ROOT / 'data/processed/pilot_boston_cambridge_202401.csv'))""")
    md("""## Inventory demand proxy and counting units

Each station starts each local day at `floor(docks/2)`. In each hour, `unconstrained = inventory + arrivals - departures`; supply `max(-unconstrained,0)`, collect `max(unconstrained-docks,0)`, and clip inventory to `[0,docks]`. Netting all flows within an hour understates possible within-hour boundary encounters. All daily half-full reset supply and collection also count as work, so resetting is not free.

Daily conservation: **arrivals + boundary supply + reset supply = departures + boundary collection + reset collection**. A virtual depot balances flows. This does not demonstrate feasible routes, depot stock or timing. No cross-city balancing is assumed except the explicitly shared other-city staffing pool.

`demand_bikes` is the sum of those four correction counts: **one pickup OR one delivery is one handling action; a completed pickup-and-delivery relocation is two actions**. The base case interprets 120 bikes/shift as 120 handling actions/shift. We report a factor-two capacity scenario if the course intended 120 completed relocations instead. This unit choice requires review. Observed trips cannot reveal lost trips or actual operator rebalancing: this is a **proxy**, not either measurement. It is not the monthly arrivals-minus-departures difference.
""")
    code("""display(data.groupby('year')[['supply_bikes','collection_bikes','reset_supply_bikes','reset_collection_bikes','demand_bikes']].sum())
assert (data.arrivals + data.supply_bikes + data.reset_supply_bikes == data.departures + data.collection_bikes + data.reset_collection_bikes).all()
print('Aggregated depot conservation: PASS')""")
    md("""## Forecast trained and selected without 2026 data

Two simple candidates: previous-year same-month daily demand, and that seasonal forecast multiplied by a city growth factor capped to [0.8,1.2]. We select globally by WAPE on July-December 2025; the growth factor for this comparison uses only January-June 2025 vs the same months of 2024. The selected method is refit using 2024-2025 only, then frozen for 2026. Zero historical denominator implies growth factor one, not an invented growth estimate. Calendar-month day counts handle leap-year differences. Missing training city-months cause an error.

WAPE = total absolute city-month error / total actual proxy. It is not averaged percentage error and does not measure rider service. No 2026 actual enters model selection or staffing decisions.
""")
    code("""display(pd.read_csv(ROOT / 'results/validation_2025.csv'))
print('Held-out 2026 forecast metrics:', summary['forecast_backtest'])
print('January-August metrics:', summary['forecast_backtest_jan_aug'])
print('Boundary limitation:', summary['backtest_boundary_note'])
display(Image(filename=str(ROOT / 'results/figures/demand_forecast.png')))""")
    md("""## Real event text → prompt engineering → structured extraction → plan

The external API adapter calls the OpenAI Responses API with a versioned prompt and strict JSON Schema Structured Outputs. `OPENAI_API_KEY` is loaded from local configuration without displaying it; `OPENAI_MODEL` is configurable. Local validation checks types, nulls, dates, source URL and literal evidence. These checks do not prove semantic correctness. Short official-source excerpts and their provenance are saved in `fixtures/`; no audience size is invented. Athlete counts are not assumed to be crowd sizes. Multi-city ambiguity can leave city null.

The code below displays the actual extraction mode, API evidence and evaluation. **Fixture mode** uses agent-authored contract fixtures with zero API calls and no model accuracy. **Recorded mode** replays saved real API results after validating their source/prompt provenance; it avoids another paid call on Notebook reruns. Draft reference annotations require actual team human review, so agreement with these drafts is provisional and is not a human-gold accuracy claim. The score covers five fields per event; ambiguity text needs a separate review. The HOCR response contains a knowledge-like claim beyond the supplied excerpt, which remains flagged rather than silently corrected. HTTP mocks test the adapter, not a real model. Configure `OPENAI_API_KEY` locally and run `python -m bluebikes.events --mode live --output results/event_extraction_live.json` for actual evidence. Never paste a key into this Notebook or commit it.

Recurring event effects may already be in monthly seasonality. Default extra demand is **zero**. We also show an explicitly assumed **+3,000 handling actions per eligible event** scenario, prorated across months. This coefficient is not extracted from text and is not calibrated on 2026 outcomes. Event source dates extend into 2026: the nonzero comparison is **retrospective stress analysis**, not a forecast possible with information available in January 2026.
""")
    code("""from bluebikes.events import load_documents, extraction_payload
docs = load_documents(ROOT)
print('Example real source excerpt:', docs[0]['source_text'])
print('Source URL:', docs[0]['source_url'])
print('Versioned system prompt:')
print((ROOT / 'prompts/event_extraction_v1.txt').read_text())
events = json.loads((ROOT / 'results/event_extraction.json').read_text())
print('Extraction status:', events['status'], 'API evidence calls:', events['api_calls'])
print('Previously recorded real API calls:', events.get('recorded_api_calls',0))
display(pd.DataFrame(events['events'])[['event_name','start_date','end_date','location','city','expected_crowd_size','ambiguities']])
print('Representative actual API extraction:' if events['live_llm_verified'] else 'Representative agent-authored fixture (not an API response):')
print(json.dumps(events['events'][0],indent=2,ensure_ascii=False))
display(pd.DataFrame(events.get('calls',[]),columns=['source_id','model','response_status','latency_seconds','executed_at_utc']))
evaluation = json.loads((ROOT / 'results/event_extraction_evaluation.json').read_text())
print('Actual model snapshots:', evaluation['actual_model_snapshots'])
print('Exact agreement with frozen draft labels:', evaluation['correct_fields'], '/', evaluation['total_fields'])
print('Reference status:', evaluation['reference_status'])
display(pd.DataFrame(evaluation['by_field']))
display(pd.DataFrame(evaluation['disagreements']))
fixture = json.loads((ROOT / 'results/event_extraction_fixture.json').read_text())
display(pd.DataFrame([
    {'mode':'fixture contract','live_outputs':False,'new_api_calls':fixture['api_calls'],'recorded_api_calls':0,'model_agreement':None},
    {'mode':events['mode'],'live_outputs':events['live_llm_verified'],'new_api_calls':events['api_calls'],'recorded_api_calls':events.get('recorded_api_calls',0),'model_agreement':evaluation['exact_agreement']}
]))
print('Recorded token usage:', evaluation['input_tokens'], 'input,', evaluation['output_tokens'], 'output')
print('Semantic caveat outside scored fields:', evaluation['unscored_review_caveat'])
print('Human-reviewed gold labels complete:', evaluation['human_review_complete'])""")
    md("""## Staffing model and cost

One crew is a driver plus van. Monthly capacity = `120 × 6 × calendar_days/7`. This is an aggregate budget; daily station service and route feasibility are not guaranteed. Existing January crews are assumed full-time: Boston 6, Cambridge 4, Somerville 1, Brookline 1, other cities share 2. January is fixed because no December 2025 hiring decision is assumed.

Full-time costs $54,000/12 + $1,500 = **$6,000/month**. Hiring takes one month; termination takes one month's notice plus **$13,500** severance. Seasonal costs **$7,800/month**, starts the following month, lasts at least three months, and is capped at eight active crews system-wide. Late starts include mandatory 2027 costs. December full-time crews continue; their January 2027 payroll run rate is disclosed separately. No annual fixed-term employment commitment is inferred. This creates a remaining full-time horizon effect, especially for late-year hires.

The mixed-integer objective minimizes 2026 payroll/severance + mandatory seasonal tail + an **assumed** service penalty. Expected loss is `0.40×0 + 0.45×3.25 + 0.15×(3.25+25) = $5.70` **per affected rider encounter**. The conversion from an uncovered proxy action to encounters is unknown. Base ratio one and alternatives 0/0.5/1/2 are scenario assumptions; crew costs, uncovered tasks, and assumed loss remain separate. The solver result is conditional on these assumptions and its reported gap.

Default other-city pooling is an explicit exception to the city-only rule. The table shows integer crews for five staffing groups. A separate city table allocates the shared pool's forecast-proportional capacity; fractional values are **capacity shares, not dedicated crews**. Do not sum repeated group counts across cities. A dedicated-city scenario allocates the initial other two crews to the two largest forecast demands and models each city separately. This choice requires review.
""")
    code("""plan = pd.read_csv(ROOT / 'results/plan_2026.csv')
for measure in ['full_time','seasonal']:
    print(measure)
    display(plan.pivot(index='city', columns='month', values=measure))
display(plan[['city','month','hires_decision','fires_notice','seasonal_start_decision','seasonal_starts','crew_cost','terminal_seasonal_cost']].loc[lambda t:(t.hires_decision+t.fires_notice+t.seasonal_start_decision+t.seasonal_starts+t.terminal_seasonal_cost)>0])
print('Proposed summary:', json.dumps(summary['proposed'], indent=2))
display(Image(filename=str(ROOT / 'results/figures/crew_plan.png')))""")
    code("""allocation = pd.read_csv(ROOT / 'results/city_capacity_allocation_2026.csv')
for measure in ['full_time_capacity_share','seasonal_capacity_share']:
    print(measure, '(shared-city fractions are capacity shares)')
    display(allocation.pivot(index='city',columns='month',values=measure).round(2))
delta = pd.read_csv(ROOT / 'results/event_plan_delta.csv')
print('Event scenario staffing changes; sources collected retrospectively:')
display(delta[(delta.full_time_change != 0) | (delta.seasonal_change != 0)])
print('Dedicated-city alternative:', json.dumps(summary['dedicated_city_scenario'],indent=2))""")
    md("""## Held-out backtest and sensitivity

Evaluate frozen plans on January-September 2026 real-data inventory proxies. Compare maintaining initial crews against proposed staffing and the retrospective event stress scenario. No plan is refit on these actuals. Capacity cannot be carried across months or staffing groups. Other-city pooling can mask within-pool shortfalls and has no route guarantee.

Demand ±20% scales the derived proxy, not a full recomputation of nonlinear inventory under synthetic ridership. E-bike shares are measured from matched departure endpoints. A 10% capacity reduction is an assumed operational stress, not an estimated e-bike causal effect. Base case has no e-bike penalty. A separate factor-two capacity scenario addresses handling vs completed relocation units.
""")
    code("""display(pd.read_csv(ROOT / 'results/backtest_comparison.csv'))
print('Base vs retrospective event WAPE:', summary['forecast_backtest']['wape'], summary['event_scenario_backtest']['wape'])
display(Image(filename=str(ROOT / 'results/figures/backtest_shortfall.png')))
display(pd.read_csv(ROOT / 'results/sensitivity.csv'))
display(Image(filename=str(ROOT / 'results/figures/demand_sensitivity.png')))
display(pd.read_csv(ROOT / 'results/loss_conversion_sensitivity.csv')[['assumed_users_per_uncovered_proxy_bike','total_committed_crew_cost','unmet_proxy_bikes','assumed_service_loss','max_simultaneous_seasonal']])
ebike = data.groupby('year')[['ebike_departures','departures']].sum()
ebike['matched_departure_ebike_share'] = ebike.ebike_departures / ebike.departures
display(ebike)""")
    md("""## Verification

Synthetic, hand-checkable examples exercise station inventory, daily reset conservation, endpoint timing and cross-chunk deduplication, calendar capacity, hire delay, firing notice, severance, seasonal minimum duration, system cap, November/December commitments, frozen-plan evaluation, and changing capacity assumptions. A separate test poisons 2026 observations and confirms the forecast is unchanged. Mock API tests do not establish real API performance.
""")
    code("""check = subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,capture_output=True,text=True)
print(check.stdout + check.stderr)
assert check.returncode == 0, 'Test failure: do not submit'
assert (plan.groupby('month').seasonal.sum() <= 8).all()
assert plan[plan.month==1].full_time.sum() == 14
print('Notebook verification PASS. Submission remains incomplete; see required remaining items below.')""")
    md("""## Demo, sources, AI use and remaining work

`docs/DEMO_SCRIPT.md` is an English three-minute draft regenerated from the same `results/summary.json` used for these figures. `docs/architecture.md` contains the diagram/storyboard. The demo still needs a team-reviewed script, rehearsal, screen recording, upload and a teaching-team-accessible link. No recording or upload is claimed.

The implementation, explanations, draft annotations and script were developed with an AI coding assistant. The user must review their accuracy and compliance with Northeastern's Academic Integrity and Use of AI policy. No contribution is attributed to an unresponsive member. Every member should participate in reviewing code/data, notebook/report, demo and repository; suggested review tasks are in `docs/REVIEW_CHECKLIST.md`.

Primary data sources and hashes: `data/metadata/station_source.json`, `bucket_manifest.json`, `trip_*.json`, cross-archive audit metadata; event URLs, retrieval/publication dates and excerpts: `fixtures/event_documents.json`, `docs/event_sources.md`; API reference: [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs). The course brief SHA256 is recorded without redistributing or modifying synchronized source materials.

Private repository: https://github.com/BitCoinJr/dads5250-bluebikes-planner . The teaching team needs access before submission. README explains inviting confirmed grader accounts; no invitations are sent automatically. Cached real aggregates allow code/Notebook reruns without raw trip downloads or an API key. Live LLM demonstration needs the local credential.

Highest-value next work: (1) human review of the frozen extraction labels and actual API outputs, including the unscored ambiguity caveat; (2) review proxy/capacity units, station matching and shared-city interpretation; (3) complete all-member review and record/upload the three-minute demo. TA confirmation and manual Canvas submission remain separate unresolved requirements.
""")
    code("""print('Required remaining items:')
for item in summary['unfinished']:
    print('-', item)
print('Video link: NOT RECORDED / NOT UPLOADED')
print('Teaching-team access: must be granted and verified manually')""")
    notebook=nbf.v4.new_notebook(cells=cells,metadata={"kernelspec":{"name":"python3","display_name":"Python 3","language":"python"},"language_info":{"name":"python","version":"3.13.2"}})
    return notebook


def main():
    p=argparse.ArgumentParser(); p.add_argument('--execute',action='store_true'); p.add_argument('--event-mode',choices=['fixture','recorded'],default='recorded'); args=p.parse_args()
    target=ROOT/'notebooks/bluebikes_submission.ipynb'; target.parent.mkdir(exist_ok=True)
    notebook=build(args.event_mode)
    if args.execute:
        kernel=ROOT/'build/kernels/bluebikes'; kernel.mkdir(parents=True,exist_ok=True)
        (kernel/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],'display_name':'Bluebikes project Python','language':'python'}))
        os.environ['JUPYTER_PATH']=str(ROOT/'build')
        os.environ['IPYTHONDIR']=str(ROOT/'build/ipython')
        os.environ['JUPYTER_RUNTIME_DIR']=str(ROOT/'build/runtime')
        notebook=NotebookClient(notebook,timeout=600,kernel_name='bluebikes',resources={'metadata':{'path':str(ROOT)}},allow_errors=False).execute()
    nbf.write(notebook,target)
    print(f"Wrote {target}; executed={args.execute}; code_cells={sum(c.cell_type=='code' for c in notebook.cells)}")


if __name__=='__main__':main()
