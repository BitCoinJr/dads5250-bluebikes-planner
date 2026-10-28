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

**Submission Notebook.** Implementation, prose and draft annotations were AI-assisted. Satoshi's seven event adjudications and eight conditional model topics are recorded; Vinay's README/UI contribution is evidenced by PR #1. Aditi's contribution remains unconfirmed. The TA has confirmed Group 8's Bluebikes registration; this does not certify the model assumptions or final submission.

User-supplied deadline: **28 October 2026, 23:59 ET = 29 October 2026, 12:59 JST**. The older Canvas 25 October display is reported outdated. No contact with the TA or members and no Canvas submission was automated.

Demo video: [2:55 AI-narrated walkthrough](https://github.com/BitCoinJr/dads5250-bluebikes-planner/blob/main/deliverables/demo/bluebikes_demo.mp4). [Final script, subtitles and rebuilding sources](../deliverables/demo/README.md).

See the [current submission checklist](../docs/SUBMISSION_PREP.md) for confirmed registration, access requirements and remaining member/Canvas actions, and the [human review](../docs/HUMAN_REVIEW.md) for evidence-based judgments.

This notebook reruns the analysis from small, committed **real-data aggregates**. Full raw-data acquisition is a separate reproducible command because the monthly trip files are large. Synthetic data appears only in explicitly labelled hand-count tests. Runtime API status is reported below; the frozen AI draft references remain unchanged while Satoshi's separate adjudications are shown below.
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
    md("""## Shared data and decision flow

The figure is generated from the single editable source `docs/diagrams/bluebikes_flow.mmd`. Python handles station-hour inventory, forecasting and constrained crew planning. The OpenAI API call uses prompt engineering to extract structured event JSON; Python validation and human confirmation precede an explicit user demand assumption and Apply action. January-September 2026 observations enter only held-out evaluation, with no feedback to training. Text labels identify roles without relying only on colors.

This Notebook, README and local app reuse the same cached SVG. Displaying it requires no Mermaid CDN, Node runtime or model call. Regeneration instructions are in `docs/architecture.md`; the new UI/diagram evidence belongs in `docs/verification-ui-polish.json`.
""")
    code("""from IPython.display import SVG
architecture_diagram = ROOT / 'docs/diagrams/bluebikes_flow.svg'
assert architecture_diagram.exists(), 'Regenerate the canonical diagram with node scripts/render_architecture.mjs'
display(SVG(filename=str(architecture_diagram)))""")
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
    md("""## Hand-counted units: synthetic stations, not observed trips

Two stations each have four docks and begin with two bikes. Four A-to-B customer trips require two boundary supplies at A and two collections at B, followed by two reset supplies and two reset collections: **8 station handling actions**. Under explicit pickup/delivery pairing, that is **4 relocation tasks**, possibly involving repeated physical bikes. The reverse-hour example has zero daily customer net at each station but still needs eight actions. An unbalanced external-depot example cannot be automatically halved.

The course's **120 bikes/shift and six shifts/week remain unchanged**. Interpretation 1 maps one handling action to one course-bike unit; interpretation 2 maps two actions to one course-bike unit under a pairing assumption. January capacity is 120 * 6 * 31/7 = 3,188.57 course-bike units under both. Converting that budget to handling actions gives 3,188.57 or 6,377.14 actions. Routing, depot endpoint work and timing are not proved by this conversion.
""")
    code("""print('SYNTHETIC HAND COUNTS - separate from observed Bluebikes data')
display(pd.read_csv(ROOT / 'results/unit_example_hourly_steps.csv'))
display(pd.read_csv(ROOT / 'results/unit_example_daily_reset.csv'))
display(pd.read_csv(ROOT / 'results/unit_example_case_summary.csv'))
display(pd.read_csv(ROOT / 'results/unit_example_monthly_capacity.csv'))
display(Image(filename=str(ROOT / 'results/figures/handling_unit_demo.png')))""")
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

The external API adapter calls the OpenAI Responses API with a versioned prompt and strict JSON Schema Structured Outputs. `OPENAI_API_KEY` is loaded from local configuration without displaying it; `OPENAI_MODEL` is configurable. Local validation checks types, nulls, dates, source URL and literal evidence. These checks do not prove semantic correctness. Short official-source excerpts and their provenance are saved in `fixtures/`. The prompt instructs the model to leave unstated audience sizes null and avoid treating athletes as spectators; the separate challenge below exposes a real violation of those instructions. Multi-city ambiguity can leave city null.

The code below displays the actual extraction mode, API evidence and evaluation. **Fixture mode** uses agent-authored contract fixtures with zero API calls and no model accuracy. **Recorded mode** replays saved real API results after validating their source/prompt provenance; it avoids another paid call on Notebook reruns. Agreement remains against frozen AI draft references, not a recomputed human-gold accuracy score. Satoshi's seven adjudications are a separate later record. The score covers five fields per event; ambiguity text needs a separate review. The HOCR response contains a knowledge-like claim beyond the supplied excerpt, which remains flagged rather than silently corrected. HTTP mocks test the adapter, not a real model. For an optional new call, configure `OPENAI_API_KEY` locally and use the app's explicit **Extract with OpenAI** button; its new response stays in session memory. Do not rerun the legacy live CLI in this evidence checkout: it internally writes the canonical live artifact even when a different `--output` path is supplied. CLI experiments need an independent copy/versioned run. This Notebook's recorded mode continues using the original artifact. Never paste a key into this Notebook or commit it.

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
    md("""## Separate added audience-count challenge and human review

The original four cases and 19/20 (95%) provisional agreement are preserved unchanged. The added cases use separate real API calls and frozen draft references, and are scored separately. Two positive sources describe the same HOCR event and are correlated; they are not three independent event forecasts. This deliberately selected challenge is not a generalization estimate.

The input sources distinguish spectators from rowers/competitors and retain approximate/lower-bound wording. The added run correctly extracts the numeric audience in both positive cases, but fails the participant-only case by using participants as crowd and inventing absent dates. Quantity qualifiers are retained in the source/reference annotations; the model omits them in its ambiguity output. The original integer schema cannot encode a qualifier in its numeric field. Preserve these failures for review. **No added case is fed into staffing or added to the event calendar.** Satoshi's case verdicts and separate annotations are now recorded; adjudicated does not mean all-pass or raw-output corrected.
""")
    code("""if summary.get('additional_event_evaluation'):
    extra = json.loads((ROOT / 'results/event_extraction_additional_evaluation.json').read_text())
    print('SEPARATE ADDED EVALUATION:', extra['correct_fields'], '/', extra['total_fields'])
    print('Original baseline remains:', summary['event_extraction_evaluation']['correct_fields'], '/', summary['event_extraction_evaluation']['total_fields'])
    display(pd.DataFrame(extra['audience_checks']))
    display(pd.DataFrame(extra['disagreements']))
    review = pd.read_csv(ROOT / 'results/event_extraction_additional_review.csv',keep_default_na=False)
    display(review[['source_id','input_excerpt','reference_json','llm_output_json','crowd_qualifier_annotation','human_judgment','human_review_status']])
    from bluebikes.human_review import status_text
    print(status_text(ROOT))
else:
    print('Supplemental real outputs are not evaluated in this fixture-mode run.')""")
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
    md('## Current human adjudication — separate from the frozen run\n\nSatoshi Nakamura explicitly adjudicated seven saved-excerpt cases and conditionally accepted eight model topics. Method: **AI-assisted review, explicitly adjudicated by Satoshi in chat**. Record compiled **2026-10-27 JST**; individual decision times were not recorded. Three accepted original cases, three HOCR annotation cases, and one participant/date failure are distinguished. **Adjudicated does not mean output corrected or all passed.**\n\nOriginal raw responses, frozen inputs/references and 19/20 and 11/15 scores are unchanged. Prior automatic summary flags and execution evidence describe the earlier pre-adjudication run, not the current human-review status. This Notebook preserves previous computational outputs and refreshes only review display cells for this integration; no full numerical rerun or new API call was performed.\n\nSee [full human annotations](../docs/HUMAN_REVIEW.md), [eight conditional model topics and shared/dedicated comparison](../docs/MODEL_REVIEW.md), and [unchanged decision record](../docs/human_review_decisions.json). Nominal 120 bikes/shift differs from the fixed-staffing e-bike stress of 108 equivalent bikes/shift. Forecast/backtest and stress tests are within the recorded interpretive scope, not empirical validation. TA registration is confirmed and the AI-narrated video is available. The [current submission checklist](../docs/SUBMISSION_PREP.md) identifies the remaining listening, member and Canvas actions; public access is verified.\n')
    code("from bluebikes.human_review import load_reviews, annotation_lines, status_text\nadjudications = load_reviews(ROOT)\nprint(status_text(ROOT))\ndisplay(pd.DataFrame([\n    {'Source ID': source_id,\n     'Human case judgment': entry['decision']['human_judgment'],\n     'Separate human annotation (raw output unchanged)': ' '.join(annotation_lines(entry, adjudications['record'])),\n     'Reviewer': entry['decision']['human_reviewer'],\n     'Compiled date (not decision time)': adjudications['record']['record_compiled_date_jst'] + ' JST',\n     'Output SHA256': entry['decision']['output_sha256']}\n    for source_id, entry in adjudications['events'].items()\n]).style.set_properties(**{'white-space':'pre-wrap','text-align':'left','vertical-align':'top','max-width':'360px'}).hide(axis='index'))\n")
    md("""## Demo checkpoint: event text to city-month and crew cost

The original saved real Marathon extraction maps to Boston in April using the documented route-endpoint convention.

The no-event baseline is an optimized model plan, not observed Bluebikes staffing. Initial crews are course-provided starting conditions, not an audited current deployment.
 The focused scenario adds **3,000 handling actions**, an **uncalibrated policy assumption**, to that city-month and reruns the existing monthly planner. The source fact and the demand coefficient are separate. The full-calendar scenario is also retained. Both are **retrospective scenarios**, not demonstrated forecast improvement. Contract decisions can propagate to months without an event, so the monthly chain and the complete plan are both shown.
""")
    code("""display(pd.read_csv(ROOT / 'results/focused_event_city_month_inputs.csv')[['event_name','start_date','city','year','month','source_url','event_increment_handling_actions']])
chain = pd.read_csv(ROOT / 'results/focused_event_chain.csv')
cols = ['city','month','event_increment_handling_actions','demand_bikes_base','demand_bikes_scenario','full_time_base','full_time_scenario','seasonal_base','seasonal_scenario','crew_cost_base','crew_cost_scenario','unmet_bikes_base','unmet_bikes_scenario']
display(chain[(chain.has_event_input) | (chain.has_staffing_or_cost_change)][cols])
display(Image(filename=str(ROOT / 'results/figures/event_demo_chain.png')))
print('UNcalibrated retrospective scenario; do not describe this as proven forecasting gain.')""")
    md('## Geographic comparison: same month, same scale\n\nThis offline station-coordinate comparison uses the same saved focused Marathon scenario as the crew/cost chain. Both panels show April 2026 on fixed common axes and one bubble-area-per-crew scale across all months. Small dots are station locations, not station demand. The four dedicated-city bubbles sit at mean station coordinates, not crew bases or event venues; the nine-city shared pool stays separate. No event marker, geocoding, tile service or new solve is used. The +3,000 handling-action increment remains an uncalibrated retrospective assumption. In the app, one month selector changes both panels without replanning.\n')
    code("from bluebikes.geography import geographic_result_from_chain, load_stations, render_geography\nfrom IPython.display import Markdown\ngeographic_view = render_geography(\n    geographic_result_from_chain(pd.read_csv(ROOT / 'results/focused_event_chain.csv')),\n    4, load_stations(ROOT))\nassert geographic_view['figure'] is not None\ndisplay(geographic_view['figure'])\ndisplay(Markdown(geographic_view['pool_md'] + '\\n\\n' + geographic_view['note_md']))")
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

Demand ±20% scales the derived proxy, not a full recomputation of nonlinear inventory under synthetic ridership. E-bike shares are measured from matched departure endpoints. A 10% effective-capacity reduction (120 nominal course bikes/shift times assumed productivity 0.9) is an operational stress assumption, not an estimated e-bike causal effect. Base case has no e-bike penalty. Separate factor-two counting-conversion scenarios address handling versus paired relocations while keeping 120 course bikes/shift fixed.
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
    md("""## Same-period cash cost, shortages and unit interpretation

The table keeps the period, demand basis and staffing scenario explicit. January-September rows compare cash costs and observed-proxy shortages over those same nine months. January-December rows compare annual cash costs and forecast-proxy shortages over those same twelve months; mandatory 2027 seasonal obligations are a separate column. Ordinary backtest plans are identified separately from retrospective event scenarios.

The earlier factor-two sensitivity holds staffing fixed, so its crew counts and cash costs do not change. The new comparison reruns the same planner on converted course-bike units while keeping **120 bikes/shift** and the assumed loss per uncovered handling action fixed. A changed headcount or cost is conditional on that unit convention, not measured productivity. This leaves routing and unbalanced depot flows unresolved.
""")
    code("""periods = pd.read_csv(ROOT / 'results/scenario_period_comparison.csv')
view = ['scenario','period','demand_basis','crew_cash_cost_in_period','uncovered_handling_actions','peak_full_time_crews_in_period','peak_seasonal_crews_in_period','mandatory_seasonal_tail_cost_2027_separate']
print('ORDINARY JAN-SEP BACKTEST - matched nine-month cost and service horizon')
display(periods[(periods.period_months==9)&periods.scenario.isin(['initial_crews_factor1','proposal_no_event_factor1'])][view])
print('RETROSPECTIVE EVENT SCENARIOS - same nine-month evaluation, no forecast-improvement claim')
display(periods[(periods.period_months==9)&periods.scenario.isin(['focused_marathon_plus3000_factor1','calendar_plus3000_factor1'])][view])
print('UNIT INTERPRETATION - newly planned counts, same-period costs and handling-action shortfalls')
units = pd.read_csv(ROOT / 'results/unit_interpretation_comparison.csv')
display(units[units.scenario.isin(['proposal_no_event_factor1','replanned_no_event_factor2'])][['scenario','period','handling_actions_per_course_bike','course_bikes_per_shift','full_time_crew_months_in_period','seasonal_crew_months_in_period','peak_total_crews_in_period','crew_cash_cost_in_period','uncovered_handling_actions']])
assert (units.course_bikes_per_shift==120).all()""")
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

The compact `notebooks/bluebikes_demo.ipynb` presents the same analysis. [Watch the 2:55 demo](../deliverables/demo/bluebikes_demo.mp4); [production sources and synchronized subtitles](../deliverables/demo/README.md) disclose the local synthetic narration and real app capture. `docs/architecture.md` explains the diagram. Final full-video/member review is tracked separately; signed-out public access is verified.

The implementation, explanations, draft annotations and script were developed with an AI coding assistant. The team is responsible for reviewing their accuracy and compliance with Northeastern's Academic Integrity and Use of AI policy. Every member should participate in reviewing code/data, notebook/report, demo and repository; suggested review tasks are in `docs/REVIEW_CHECKLIST.md`.

Primary data sources and hashes: `data/metadata/station_source.json`, `bucket_manifest.json`, `trip_*.json`, cross-archive audit metadata; event URLs, retrieval/publication dates and excerpts: `fixtures/event_documents.json`, `docs/event_sources.md`, and the separate `fixtures/event_documents_additional.json` / `docs/event_sources_additional.md`; API reference: [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs). The course brief SHA256 is recorded without redistributing or modifying synchronized source materials.

Repository: https://github.com/BitCoinJr/dads5250-bluebikes-planner . The TA requires public access before submission; current publication/access status is in the submission checklist. Cached real aggregates and saved responses allow replay without raw trip downloads or an API key.

Remaining actions: final full-video review, truthful member contributions and Canvas submission. Publication and signed-out access checks are complete. TA registration is confirmed. Numerical results remain conditional on the disclosed data and operating assumptions.
""")
    code(r"""from pathlib import Path
from IPython.display import Markdown, display
status_root = Path.cwd()
if not (status_root / 'docs').exists(): status_root = status_root.parent
import re
status_markdown = (status_root / 'docs/SUBMISSION_PREP.md').read_text(encoding='utf-8')
status_markdown = re.sub(r'\]\((?![a-zA-Z]+:|#|/)', '](../docs/', status_markdown)
display(Markdown(status_markdown))""")
    md("""## Optional local Gradio app — off by default

Install the current `requirements.txt` before opting in. Leave `LAUNCH_LOCAL_APP = False` for a normal top-to-bottom execution or submitted artifact: this cell starts no server and makes no live API call. To interact locally, set the flag to `True` and run the cell. The default port remains 7860; for this polished revision's review set `LOCAL_APP_PORT = 7876`, equivalent to `python scripts/run_app.py --port 7876`, to avoid an older process on 7860. It binds to **127.0.0.1**, with sharing and analytics disabled. The standalone app and Notebook are two launchers for the same application.

The initial view uses saved real extraction/results. Only the explicit **Extract with OpenAI** button can request a new model response; opening the app does not. Reviews are session-only and do not overwrite frozen API outputs, references or evaluation artifacts. Inspect the source, JSON, editable fields and ambiguities; explain corrections in review notes; click **Confirm reviewed values (this session only)** and then **Apply to plan**. Edits to the event or assumptions invalidate the applied scenario and require another apply; stale results must not be treated as current. Source changes require replay/extraction and review again.

The +3,000 increment remains an uncalibrated retrospective assumption. Unit interpretation keeps 120 course bikes/shift fixed and separates handling actions from conditionally paired relocations. Hiring decisions take effect the following month. Annual forecast/cost comparisons remain separate from January-September observed-proxy/cost comparisons. Original 19/20 and separate 11/15 provisional agreements, including the participant/date failure and Satoshi's separate annotations, remain visible.

When finished, run **`app.close()`** in a new cell, or set the flag back to `False` and rerun this cell. Stop a standalone process with **Ctrl+C**. Return the flag to `False` before saving/executing the submission. App and Notebook verification is tracked separately in `docs/verification-gradio.json`; a link alone is not evidence of a successful run.
""")
    code("""LAUNCH_LOCAL_APP = False
LOCAL_APP_PORT = 7860
if LAUNCH_LOCAL_APP:
    from bluebikes.app import launch_local
    if 'app' in globals() and app is not None:
        app.close()
    app = launch_local(ROOT, port=LOCAL_APP_PORT, inline=True, prevent_thread_lock=True)
else:
    if 'app' in globals() and app is not None:
        app.close()
        app = None
    print('Local app is OFF. Set LAUNCH_LOCAL_APP=True only for an interactive local session.')
# To stop an app you explicitly started, run app.close() in a new cell.
# Restore LAUNCH_LOCAL_APP=False before saving or executing the submitted Notebook.""")
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
