"""Build the short, executed recording view from the audited analysis outputs."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def build():
    cells = []
    def md(text): cells.append(nbf.v4.new_markdown_cell(text))
    def code(text): cells.append(nbf.v4.new_code_cell(text))

    md("""# Bluebikes: three-minute review demo

DADS5250 / Group 8. The [2:55 video, script and subtitles](../deliverables/demo/README.md) are available. Satoshi's seven case adjudications and eight conditional model topics are recorded; Vinay's PR #1 documents his review. TA registration is confirmed. Aditi's contribution, final access verification and Canvas submission remain unconfirmed. This view replays genuine saved OpenAI calls with hash validation and makes **zero new API calls**. Fixtures are not shown as model outputs. Run the submission Notebook first to regenerate analysis tables.

## 1. The problem and ordinary backtest

Train/select on 2024-2025; freeze the plan; evaluate against the January-September 2026 observed-trip inventory proxy. Costs and shortages below cover **the same nine months**. The proxy is neither lost trips nor measured operator work; archive gaps and current-station matching limitations remain. [Full audit](bluebikes_submission.ipynb), [English script](../docs/DEMO_SCRIPT.md), [recording run sheet and timing log](../docs/RECORDING_RUNSHEET.md).
""")
    code("""from pathlib import Path
import sys, json
import pandas as pd
from IPython.display import display, Image
ROOT = Path.cwd()
if not (ROOT / 'bluebikes').exists(): ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
pd.set_option('display.max_colwidth', 140)
from bluebikes.events import run_extraction, load_documents
from bluebikes.event_validation import run_additional_evaluation
original = run_extraction('recorded', root=ROOT)
assert original['live_llm_verified'] and original['api_calls'] == 0
assert original['evaluation']['correct_fields'] == 19
assert original['evaluation']['total_fields'] == 20
periods = pd.read_csv(ROOT / 'results/scenario_period_comparison.csv')
ordinary = periods[(periods.period_months == 9) & periods.scenario.isin(['initial_crews_factor1','proposal_no_event_factor1'])]
columns = ['scenario','period','crew_cash_cost_in_period','uncovered_handling_actions','peak_total_crews_in_period']
display(ordinary[columns].round(2))
print('Ordinary frozen-plan backtest. Historical original API calls:', original['recorded_api_calls'], '; new API calls:', original['api_calls'])""")
    md("""## Shared flow and visible roles

Read the cached diagram from historical trip/station inputs to the frozen forecast, and from official event text through an OpenAI API call, prompt engineering and structured JSON extraction. Python validates; a human confirms; an explicit user demand assumption and Apply action gate the Python crew optimizer. Held-out 2026 January-September trips feed backtesting only, with no return path to training. The app and README use this same generated SVG from `docs/diagrams/bluebikes_flow.mmd`, without a Mermaid CDN or runtime Node requirement.
""")
    code("""from IPython.display import SVG
architecture_diagram = ROOT / 'docs/diagrams/bluebikes_flow.svg'
assert architecture_diagram.exists(), 'Regenerate the canonical diagram with node scripts/render_architecture.mjs'
display(SVG(filename=str(architecture_diagram)))""")
    md("""## 2. Actual announcement to actual LLM extraction

The input is a preserved real-source excerpt. The output below is a **recorded actual OpenAI response**, not the fixture. The model assigns the route to its named Boston endpoint; that city allocation is an explicit convention needing review. Crowd is null because the original announcement's 30,000 athletes are not a spectator estimate.
""")
    code("""doc = load_documents(ROOT)[0]
event = original['events'][0]
print('Source:', doc['source_url'])
print('INPUT EXCERPT:', doc['source_text'])
print('ACTUAL STRUCTURED OUTPUT:')
print(json.dumps(event, indent=2))
print('API provenance:')
display(pd.DataFrame(original['calls'])[['source_id','model','executed_at_utc','response_status']].head(1))""")
    md("""## 3. City and month to a conditional crew decision

**Retrospective scenario: +3,000 handling actions is an uncalibrated assumption, not an extracted fact or evidence of improved forecasting.**

The no-event baseline is an optimized model plan, not observed Bluebikes staffing. Initial crews are course-provided starting conditions, not an audited current deployment.
 Only the original Marathon record is used for this focused scenario. The existing planner adds the increment to Boston/April and resolves annual staffing constraints. April payroll and April shortage share a one-month horizon; annual hiring/contracts can change other months too. The ordinary backtest remains separate.
""")
    code("""inputs = pd.read_csv(ROOT / 'results/focused_event_city_month_inputs.csv')
display(inputs[['event_name','start_date','city','year','month','event_increment_handling_actions','source_url']])
chain = pd.read_csv(ROOT / 'results/focused_event_chain.csv')
april = chain[(chain.city == 'Boston') & (chain.month == 4)]
display(april[['city','month','demand_bikes_base','demand_bikes_scenario','full_time_base','full_time_scenario','seasonal_base','seasonal_scenario','crew_cost_base','crew_cost_scenario','unmet_bikes_base','unmet_bikes_scenario']].round(2))
assert april.event_increment_handling_actions.iloc[0] == 3000
assert april.full_time_scenario.iloc[0] > april.full_time_base.iloc[0]
display(Image(filename=str(ROOT / 'results/figures/event_demo_chain.png')))
print('Whole-plan nine-month evaluation: retrospective only; no causal/forecast-improvement claim')
display(periods[(periods.period_months == 9) & periods.scenario.isin(['proposal_no_event_factor1','focused_marathon_plus3000_factor1'])][columns].round(2))""")
    md('## Geographic comparison: same month, same scale\n\nThis offline station-coordinate comparison uses the same saved focused Marathon scenario as the crew/cost chain. Both panels show April 2026 on fixed common axes and one bubble-area-per-crew scale across all months. Small dots are station locations, not station demand. The four dedicated-city bubbles sit at mean station coordinates, not crew bases or event venues; the nine-city shared pool stays separate. No event marker, geocoding, tile service or new solve is used. The +3,000 handling-action increment remains an uncalibrated retrospective assumption. In the app, one month selector changes both panels without replanning.\n')
    code("from bluebikes.geography import geographic_result_from_chain, load_stations, render_geography\nfrom IPython.display import Markdown\ngeographic_view = render_geography(\n    geographic_result_from_chain(pd.read_csv(ROOT / 'results/focused_event_chain.csv')),\n    4, load_stations(ROOT))\nassert geographic_view['figure'] is not None\ndisplay(geographic_view['figure'])\ndisplay(Markdown(geographic_view['pool_md'] + '\\n\\n' + geographic_view['note_md']))")
    md("""## 4. Hand count: eight station actions versus four relocations

**Synthetic, hand-checkable example:** both stations have four docks and start with two bikes. Four A-to-B customer trips cause two supplies at A and two collections at B. Resetting both stations to half full adds two supplies and two collections: **8 handling actions**. Pairing pickup and delivery gives **4 relocation tasks**, possibly reusing physical bikes. A reverse-hour example has zero daily customer net but still requires action; the unbalanced-depot example cannot automatically be halved.

**120 bikes/shift remains unchanged.** The two interpretations change the conversion between course-bike units and proxy actions, not the course number. In January, 120 * 6 * 31/7 = 3,188.57 course-bike units per crew. No feasible van route, depot stock or within-hour order is established.
""")
    code("""display(Image(filename=str(ROOT / 'results/figures/handling_unit_demo.png')))
display(pd.read_csv(ROOT / 'results/unit_example_case_summary.csv'))
display(pd.read_csv(ROOT / 'results/unit_example_monthly_capacity.csv').round(2))""")
    md("""## 5. What that unit assumption changes

Both rows use the **same January-September 2026 horizon** and report shortages in handling actions. Factor one maps one action to one course-bike unit; factor two assumes paired pickup/delivery and maps two actions to one course-bike unit. Replanning uses only frozen 2024-2025 forecasts; 2026 observations are evaluation only. The assumed penalty per uncovered handling action is held fixed, and **120 bikes/shift is unchanged**. These are conditional model results, not measured productivity.

The older frozen-crew sensitivity changes shortages while leaving crew counts/costs unchanged. This table instead reruns staffing optimization under the alternate conversion. Annual comparisons and 2027 seasonal obligations are in the full audit.
""")
    code("""units = pd.read_csv(ROOT / 'results/unit_interpretation_comparison.csv')
units = units[(units.period_months == 9) & units.scenario.isin(['proposal_no_event_factor1','replanned_no_event_factor2'])]
assert (units.course_bikes_per_shift == 120).all()
display(units[['scenario','period','handling_actions_per_course_bike','course_bikes_per_shift','peak_total_crews_in_period','full_time_crew_months_in_period','seasonal_crew_months_in_period','crew_cash_cost_in_period','uncovered_handling_actions']].round(2))""")
    md("""## 6. Separate audience challenge: failure stays visible

The original four calls retain **19/20 = 95%** against frozen, **AI-authored provisional labels**. The three new actual calls score **11/15 = 73.33%** separately; neither score is a human-gold accuracy estimate. Two positive spectator sources describe the **same** regatta (correlated, not two independent events). Both numeric spectator counts match; the participant-only case incorrectly outputs 30,000 spectators and unsupported dates. Source quantity qualifiers are preserved in annotations but missing from the model's ambiguity explanation.

These added records are **evaluation only** and never enter the demand adjustment. The table juxtaposes input, provisional reference, actual model output and Satoshi's recorded human judgment. Full unabridged JSON/evidence and editable judgment columns: [review CSV](../results/event_extraction_additional_review.csv); [review notes](../docs/human_review_additional.md). All three added cases are adjudicated: two require separate annotations and one fails grounding; no raw response is rewritten.
""")
    code("""additional = run_additional_evaluation('recorded', root=ROOT)
assert additional['live_llm_verified'] and additional['api_calls'] == 0
metrics = additional['evaluation']
assert (metrics['correct_fields'], metrics['total_fields']) == (11, 15)
print('Separate actual-call evaluation:', metrics['correct_fields'], '/', metrics['total_fields'])
print('Recorded additional calls:', additional['recorded_api_calls'], '; new API calls:', additional['api_calls'])
review = pd.read_csv(ROOT / 'results/event_extraction_additional_review.csv', keep_default_na=False)
def concise(raw):
    obj = json.loads(raw)
    return json.dumps({k: obj[k] for k in ['start_date','end_date','location','city','expected_crowd_size','ambiguities']}, indent=2)
view = pd.DataFrame({'Input excerpt + source':review.input_excerpt + '\\n' + review.source_url,
                     'Provisional reference (AI draft)':review.reference_json.map(concise),
                     'Actual LLM output':review.llm_output_json.map(concise),
                     'Human judgment':review.human_judgment,
                     'Review status':review.human_review_status})
display(view.style.set_properties(**{'white-space':'pre-wrap','text-align':'left','vertical-align':'top','min-width':'180px','max-width':'350px'}).hide(axis='index'))
display(pd.DataFrame(metrics['disagreements']))
from bluebikes.human_review import status_text
print(status_text(ROOT))
print('All additional cases: evaluation only. Demo video: deliverables/demo/bluebikes_demo.mp4')""")
    md('## Current human adjudication — separate from the frozen run\n\nSatoshi Nakamura explicitly adjudicated seven saved-excerpt cases and conditionally accepted eight model topics. Method: **AI-assisted review, explicitly adjudicated by Satoshi in chat**. Record compiled **2026-10-27 JST**; individual decision times were not recorded. Three accepted original cases, three HOCR annotation cases, and one participant/date failure are distinguished. **Adjudicated does not mean output corrected or all passed.**\n\nOriginal raw responses, frozen inputs/references and 19/20 and 11/15 scores are unchanged. Prior automatic summary flags and execution evidence describe the earlier pre-adjudication run, not the current human-review status. This Notebook preserves previous computational outputs and refreshes only review display cells for this integration; no full numerical rerun or new API call was performed.\n\nSee [full human annotations](../docs/HUMAN_REVIEW.md), [eight conditional model topics and shared/dedicated comparison](../docs/MODEL_REVIEW.md), and [unchanged decision record](../docs/human_review_decisions.json). Nominal 120 bikes/shift differs from the fixed-staffing e-bike stress of 108 equivalent bikes/shift. Forecast/backtest and stress tests are within the recorded interpretive scope, not empirical validation. TA registration is confirmed and the AI-narrated video is available. The [current submission checklist](../docs/SUBMISSION_PREP.md) identifies the remaining listening, member, access and Canvas actions.\n')
    code("from bluebikes.human_review import load_reviews, annotation_lines, status_text\nadjudications = load_reviews(ROOT)\nprint(status_text(ROOT))\ndisplay(pd.DataFrame([\n    {'Source ID': source_id,\n     'Human case judgment': entry['decision']['human_judgment'],\n     'Separate human annotation (raw output unchanged)': ' '.join(annotation_lines(entry, adjudications['record'])),\n     'Reviewer': entry['decision']['human_reviewer'],\n     'Compiled date (not decision time)': adjudications['record']['record_compiled_date_jst'] + ' JST',\n     'Output SHA256': entry['decision']['output_sha256']}\n    for source_id, entry in adjudications['events'].items()\n]).style.set_properties(**{'white-space':'pre-wrap','text-align':'left','vertical-align':'top','max-width':'360px'}).hide(axis='index'))\n")
    md("""## Architecture and recording handoff

Use the shared Mermaid figure displayed above for architecture and presentation. The API call reaches OpenAI, the versioned prompt defines fields and unknowns, and structured output supports Python validation and human-confirmed planning input. Recorded-call hashes keep the demo reproducible; structural validation does not guarantee semantic correctness.

**Remaining:** final full-video/member review, authorized publication and verified teaching-team access, then manual Canvas submission. See the [current checklist](../docs/SUBMISSION_PREP.md). Registration is confirmed and the video exists; the empirical limitations remain disclosed.
""")
    md("""## Optional interactive local app — off by default

The cells above remain the reproducible recording view. Install the current `requirements.txt` before using this optional app. Keep `LAUNCH_LOCAL_APP = False` for execution/submission: no server starts and no live API call is made. Opt in by setting it to `True` below. The default port remains 7860; set `LOCAL_APP_PORT = 7876` for this polished revision's review, matching `python scripts/run_app.py --port 7876` and avoiding an older process on 7860. The app binds to **127.0.0.1**, with sharing and analytics disabled.

Start with the saved real input/output and results. A new model call happens only through **Extract with OpenAI**. Review the editable fields and ambiguities, explain corrections in notes, click **Confirm reviewed values (this session only)**, then **Apply to plan**. Review edits stay in the session. Source, reviewed event or assumption edits invalidate an applied scenario and require another apply; a source change requires replay/extraction and review again. The frozen original four calls/19-of-20 agreement and separate three-call/11-of-15 challenge are retained, with failures and Satoshi's separate human annotations preserved.

Keep +3,000 labelled **uncalibrated retrospective**, 120 course bikes/shift fixed during unit conversion, hiring decisions distinct from next-month active crews, and annual forecast/cost results separate from January-September observed-proxy/cost results. The app does not turn these assumptions into verified operating facts.

Stop a Notebook session with **`app.close()`** in a new cell, or restore the flag to `False` and rerun this cell. Stop the standalone process with **Ctrl+C**. Save the submission with the flag `False`. See `docs/verification-gradio.json` for separately recorded integration checks; inspect the evidence before recording a demo.
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
    return nbf.v4.new_notebook(cells=cells, metadata={"kernelspec":{"name":"python3","display_name":"Python 3","language":"python"},"language_info":{"name":"python","version":"3.13.2"}})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    notebook = build()
    if args.execute:
        kernel = ROOT / 'build/kernels/bluebikes'
        kernel.mkdir(parents=True, exist_ok=True)
        (kernel / 'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],'display_name':'Bluebikes project Python','language':'python'}))
        os.environ['JUPYTER_PATH'] = str(ROOT / 'build')
        os.environ['IPYTHONDIR'] = str(ROOT / 'build/ipython')
        os.environ['JUPYTER_RUNTIME_DIR'] = str(ROOT / 'build/runtime')
        notebook = NotebookClient(notebook, timeout=120, kernel_name='bluebikes', resources={'metadata':{'path':str(ROOT)}}, allow_errors=False).execute()
    target = ROOT / 'notebooks/bluebikes_demo.ipynb'
    target.parent.mkdir(exist_ok=True)
    nbf.write(notebook, target)
    print(f"Wrote {target}; executed={args.execute}; code_cells={sum(c.cell_type=='code' for c in notebook.cells)}")


if __name__ == '__main__': main()
