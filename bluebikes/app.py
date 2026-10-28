"""One local Gradio screen; all extraction/planning rules live in AppService."""
from __future__ import annotations

import calendar
import copy
import csv
import json
from functools import lru_cache
from html import escape
import os
from pathlib import Path

# Never create an analytics request or a public tunnel from the local demo.
os.environ['GRADIO_ANALYTICS_ENABLED'] = 'False'
import gradio as gr
import pandas as pd

from .human_review import review_html
from .app_service import AppService, EVALUATION_ONLY_MESSAGE
from .events import _hash
from .presentation import render_result, executive_summary
from .geography import load_stations, render_geography

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAVED_LABEL = 'Saved real OpenAI response'
LIVE_LABEL = 'New real OpenAI response'


def _text(value):
    return '' if value is None else str(value)


def _document(state, title, url, text):
    base = (state or {}).get('document') or {}
    return {**base, 'source_title':_text(title), 'source_url':_text(url), 'source_text':_text(text)}


def _edits(start, end, city, location, crowd, ambiguities):
    return {'start_date':_text(start).strip() or None, 'end_date':_text(end).strip() or None,
            'city':_text(city).strip() or None, 'location':_text(location).strip() or None,
            'expected_crowd_size':crowd,
            'ambiguities':[line.strip() for line in _text(ambiguities).splitlines() if line.strip()]}


def _frame(records):
    return pd.DataFrame(records or [])


def _legacy_outputs(state):
    """Display state without changing the model record or any evaluation files."""
    original = state.get('original_llm')
    provenance = state.get('provenance') or {}
    label = LIVE_LABEL if provenance.get('mode') == 'live' else SAVED_LABEL
    status = f"**{label}**" if original else '**No valid extraction for the current input.**'
    labels = {'saved_ready':'Review the values before applying. No plan has been applied.',
              'live_ready':'New live extraction received. Review it before applying.',
              'review_confirmed':'Reviewed for this session. Press Apply to plan explicitly.',
              'review_changed':'Review changed; confirmation and previous plan cleared.',
              'input_changed':'Source changed; previous extraction, confirmation and plan cleared.',
              'plan_ready':'Reviewed event applied as a retrospective scenario.',
              'live_failed':'Live extraction failed; no saved fallback was substituted.',
              'saved_failed':'No valid matching saved response is loaded.',
              'apply_blocked':'Plan blocked. Review the current values and confirm again.',
              'review_failed':'Confirmation was not accepted.', 'plan_failed':'No new plan accepted.'}
    status += '\n\n' + labels.get(state.get('status'),'Extract or load matching saved evidence, then review.')
    if state.get('evaluation_only'):
        status = status.replace('Press Apply to plan explicitly.', 'This evaluation case remains excluded from planning.')
        status = status.replace('Review the values before applying. No plan has been applied.', 'Inspect the preserved output and separate human annotations below.')
        status += '\n\n**' + EVALUATION_ONLY_MESSAGE.split('. ',1)[0] + '**. ' + EVALUATION_ONLY_MESSAGE.split('. ',1)[1]
    if state.get('error'): status += '\n\n' + state['error']
    reviewed = state.get('reviewed_event')
    confirmed = bool(reviewed and state.get('review_digest'))
    result = state.get('result') or {}
    comparisons = _frame(result.get('period_comparison'))
    if len(comparisons):
        # The initial-crew benchmark stays in the audit; compare no-event vs this event here.
        if 'scenario' in comparisons:
            comparisons = comparisons[~comparisons.scenario.str.contains('initial',case=False)]
        wanted = ['scenario','period','crew_cash_cost_in_period','uncovered_handling_actions','peak_total_crews_in_period','mandatory_seasonal_tail_cost_2027_separate']
        comparisons = comparisons[[name for name in wanted if name in comparisons]].round(2)
    if len(comparisons):
        comparisons = comparisons.rename(columns={
            'scenario':'Scenario','period':'Period','crew_cash_cost_in_period':'Cash cost ($)',
            'uncovered_handling_actions':'Uncovered actions','peak_total_crews_in_period':'Peak crews',
            'mandatory_seasonal_tail_cost_2027_separate':'2027 seasonal tail ($)'})
        comparisons['Scenario'] = comparisons['Scenario'].replace({'no_event':'No-event baseline','reviewed_event':'Reviewed event'})
        comparisons['Period'] = comparisons['Period'].replace({'2026-01 through 2026-12':'Jan-Dec 2026 forecast','2026-01 through 2026-09':'Jan-Sep 2026 observed proxy'})
    full_chain = _frame(result.get('monthly_chain'))
    chain = full_chain
    notes = ''
    if result.get('summary'):
        info = result['summary']
        notes = (f"City: **{info['selected_city']}**; staffing group: **{info['selected_group']}**. "
                 f"Assumed increment: **{info['increment_handling_actions_per_event']:,.0f} handling actions**; "
                 f"conversion: **{info['handling_actions_per_course_bike']} actions/course bike**.\n\n")
        event_months = {row['month'] for row in result.get('city_month_inputs',[])}
        for row in result.get('monthly_chain',[]):
            if row['month'] in event_months:
                notes += (f"- Month **{int(row['month'])}**: FT **{int(row['full_time_base'])} -> {int(row['full_time_scenario'])}**; "
                          f"seasonal **{int(row['seasonal_base'])} -> {int(row['seasonal_scenario'])}**; "
                          f"city/group cash cost **${row['crew_cost_base']:,.0f} -> ${row['crew_cost_scenario']:,.0f}**. "
                          f"Prior hiring decision month: **{row.get('hire_decision_month_for_active_month','see audit')}**; "
                          f"hires **{int(row.get('prior_month_hires_decision_base',0))} -> {int(row.get('prior_month_hires_decision_scenario',0))}**.\n")
        notes += '\nHiring and seasonal decisions affect next-month staffing. Full-year contracts can change other months; this does not imply immediate hiring. The estimates are proxy handling shortages, not measured lost trips. The shared other-city group is a policy exception.'
    if len(chain):
        names = ['month','full_time_base','full_time_scenario','seasonal_base','seasonal_scenario',
                 'crew_cost_base','crew_cost_scenario','uncovered_handling_actions_base','uncovered_handling_actions_scenario']
        chain = chain[[name for name in names if name in chain]].round(2).rename(columns={
            'month':'Month','full_time_base':'FT baseline','full_time_scenario':'FT event',
            'seasonal_base':'Seasonal baseline','seasonal_scenario':'Seasonal event',
            'crew_cost_base':'Cost baseline ($)','crew_cost_scenario':'Cost event ($)',
            'uncovered_handling_actions_base':'Uncovered baseline actions',
            'uncovered_handling_actions_scenario':'Uncovered event actions'})
    visible_provenance = {key:provenance[key] for key in ['mode','model','executed_at_utc','source_id'] if key in provenance}
    return (state, status, original, visible_provenance, reviewed,
            gr.update(interactive=confirmed and not state.get("evaluation_only")), comparisons, chain, notes)


UI_EXTRA_KEYS = ['extraction_html','kpi_html','crew_figure','demand_figure',
                 'annual_table','backtest_table','monthly_table','explanation_md',
                 'geographic_month','geographic_figure','pool_md','geographic_note_md']

APP_CSS = """
.gradio-container {width:100%!important;min-width:0!important;max-width:1320px!important;margin:auto!important;}
.gradio-container .main,.gradio-container .wrap,.gradio-container .contain {min-width:0!important;max-width:100%;}
.bb-summary {margin:0 0 20px;line-height:1.5;color:var(--body-text-color,#172b29);}
.bb-summary h2 {font-size:1.9rem!important;line-height:1.2!important;margin:4px 0 8px!important;}
.bb-summary-lead {font-size:1.05rem;margin:0 0 20px;}
.bb-summary-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;}
.bb-summary article {min-width:0;border:1px solid var(--border-color-primary,#d6dfdb);border-radius:12px;padding:18px;overflow-wrap:anywhere;}
.bb-summary-step {font-size:.74rem;font-weight:700;letter-spacing:.07em;color:var(--body-text-color-subdued,#425e58);}
.bb-summary h3 {font-size:1.1rem!important;line-height:1.3!important;margin:10px 0!important;}
.bb-summary p {margin:9px 0;}
.bb-summary ul {padding-left:18px;margin:9px 0;font-size:.92rem;}
.bb-summary li {margin:6px 0;}
.bb-summary-caveat,.bb-summary-foot {font-size:.82rem;line-height:1.45;}
.bb-summary-demo {border-top:4px solid #438371!important;}
.bb-summary-foot {margin-top:12px!important;}
@media(min-width:641px) and (max-width:1000px) {.bb-summary-grid {grid-template-columns:repeat(2,minmax(0,1fr));}}
.bb-flow-scroll {overflow-x:auto;background:white;border:1px solid #d6dfdb;border-radius:12px;padding:12px;}
.bb-flow-scroll svg {display:block;width:100%;height:auto;min-width:1020px;}
.bb-flow-caption {font-size:.85rem;opacity:.8;margin:6px 0 16px;}
.bb-extraction {border:1px solid var(--border-color-primary,#d6dfdb);border-radius:12px;padding:16px;}
.bb-extraction dl {display:grid;grid-template-columns:minmax(110px,1fr) minmax(0,2.3fr);gap:10px 16px;margin:0;}
.bb-extraction dt {font-weight:650;font-size:.9rem;}
.bb-extraction dd {margin:0;overflow-wrap:anywhere;}
.bb-evidence {margin:14px 0 0;border-left:3px solid #766398;padding:8px 12px;font-size:.9rem;overflow-wrap:anywhere;}
.bb-review-note {margin-top:12px;padding:9px;border:1px solid #b99a58;border-radius:8px;font-size:.88rem;}
.bb-review-note ul {padding-left:18px;margin:4px 0;}
.bb-muted {font-size:.86rem;opacity:.8;}
.bb-kpis {padding:8px 0;}
.bb-kpis section {box-sizing:border-box;}
.bb-metric-grid {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;}
.bb-kpis h3 {font-size:1.3rem!important;}
.bb-null {font-style:italic;}
.bb-detail-table th {white-space:nowrap!important;word-break:normal!important;}
@media(max-width:640px) {
 .bb-summary-grid {grid-template-columns:1fr;}
 .bb-summary h2 {font-size:1.5rem!important;}
 .bb-extraction dl {grid-template-columns:1fr;gap:4px;}
 .bb-extraction dd {margin-bottom:10px;}
 .bb-flow-scroll {padding:8px;}
 .bb-kpis section {min-width:0!important;width:100%;}
 .bb-metric-grid {grid-template-columns:1fr;}
 .bb-chart {overflow-x:auto;}
 .bb-chart .matplotlib {justify-content:flex-start!important;align-items:flex-start!important;min-width:760px;}
 .bb-chart img {min-width:760px;max-width:none;}
 .bb-geo-chart .matplotlib {min-width:1180px;}
 .bb-geo-chart img {min-width:1180px;}
}
"""


@lru_cache(maxsize=4)
def _saved_review_rows(root):
    path=Path(root)/'results/event_extraction_additional_review.csv'
    if not path.is_file():return []
    with path.open(encoding='utf-8-sig',newline='') as handle:
        return list(csv.DictReader(handle))


def _extraction_cards(state, root=None):
    """Readable ORIGINAL model fields; existing exact-match review flags only.

    No new model inference or evaluation writes. Human annotations remain separate.
    Provisional automated notes are
    attached only when source input and output hash match the saved review row.
    """
    record=state.get('original_llm')
    if not record:return ''
    document=state.get('document') or {}
    flags=set(); qualifier=''
    for row in _saved_review_rows(str(root or PROJECT_ROOT)):
        if (row.get('source_url')==document.get('source_url') and
            row.get('input_excerpt')==document.get('source_text') and
            row.get('output_sha256')==_hash(record)):
            flags={note['flag'] for note in json.loads(row.get('automated_quality_notes') or '[]')}
            annotation=json.loads(row.get('crowd_qualifier_annotation') or '{}')
            if annotation.get('value')==record.get('expected_crowd_size'):
                qualifier=annotation.get('qualifier') or ''
            break
    def field(value): return escape(str(value),quote=True) if value is not None and value!='' else '<span class="bb-null">Not stated</span>'
    dates=record.get('start_date')
    if record.get('end_date') and record.get('end_date')!=dates:
        dates=(dates or 'Not stated')+' to '+record['end_date']
    date_html=field(dates)
    if 'unsupported_date_inference' in flags:
        date_html+=' <em>(unsupported inferred date; review required)</em>'
    city_venue=field(record.get('city'))+' / '+field(record.get('location'))
    count=record.get('expected_crowd_size')
    crowd_html='<span class="bb-null">Not stated</span>' if count is None else escape(f'{count:,}')
    if count is not None and qualifier:
        crowd_html=escape(qualifier)+' '+crowd_html+' <em>(source qualifier; separate annotation)</em>'
    if 'non_audience_number_used_as_crowd' in flags:
        crowd_html+=' <em>(flagged participant count, not verified spectators)</em>'
    notes=list(record.get('ambiguities') or [])
    messages={'non_audience_number_used_as_crowd':'The saved model output used participants as spectators. Correct it or leave it unknown.',
              'unsupported_date_inference':'The saved output inferred an event day absent from the excerpt.',
              'crowd_qualifier_omitted_from_ambiguities':'Keep the source quantity qualifier; the bare number is not exact attendance.',
              'geographic_explanation_requires_review':'A geographic explanation goes beyond the supplied excerpt.'}
    notes.extend(messages[flag] for flag in sorted(flags) if flag in messages)
    if count is None and any(word in document.get('source_text','').lower() for word in ['athletes','participants']):
        notes.append('Athlete or participant counts are not used as a spectator estimate.')
    if not notes: notes=['Check the date, city allocation, spectator role and source evidence before confirming.']
    needs='<ul>'+''.join('<li>'+escape(note)+'</li>' for note in notes)+'</ul>'
    values=[('Event',field(record.get('event_name'))),('Date / range',date_html),('City / venue',city_venue),('Expected spectators',crowd_html)]
    html='<section class="bb-extraction"><p class="bb-muted">Original OpenAI fields, preserved unchanged. Human adjudication, when available, is shown separately below.</p><dl>'
    html+=''.join('<dt>'+label+'</dt><dd>'+value+'</dd>' for label,value in values)+'</dl>'
    html+='<div class="bb-review-note"><strong>Needs review: original ambiguities and automated checks</strong>'+needs+'</div>'
    human_note=review_html(document, record, root)
    if state.get('evaluation_only'):
        human_note=human_note.replace('Session confirmation and Apply are still required.',
                                     'Evaluation only; session confirmation cannot authorize staffing use.')
    html+=human_note
    html+='<blockquote class="bb-evidence"><strong>Evidence excerpt</strong><br>'+escape(record.get('evidence_text') or '')+'</blockquote></section>'
    return html


def _diagram_html(root):
    path=Path(root)/'docs/diagrams/bluebikes_flow.svg'
    if not path.is_file():return '<p>Architecture image unavailable; see the README rendering command.</p>'
    svg=path.read_text(encoding='utf-8')
    return '<div class="bb-flow-scroll" aria-label="Data, reviewed event facts, explicit scenario and Python crew decisions">'+svg+'</div><p class="bb-flow-caption">OpenAI structures event facts; you confirm them. Python plans crews under an explicit demand scenario. The diagram scrolls horizontally on narrow screens.</p>'


MAP_MONTHS = [(calendar.month_name[m] + ' 2026', m) for m in range(1, 13)]
_DEFAULT_MAP_MONTH = object()


def _geographic_outputs(state, month=_DEFAULT_MAP_MONTH, root=None):
    """Render cached plans only; month selection never plans or calls an API."""
    result = state.get('result') if isinstance(state, dict) else None
    if month is _DEFAULT_MAP_MONTH and result:
        months = [r.get('month') for r in result.get('city_month_inputs', [])
                  if isinstance(r.get('month'), int) and 1 <= r['month'] <= 12]
        month = min(months) if months else 1
    empty = {'figure': None, 'pool_md': '', 'note_md': ''}
    view = empty
    available = bool(isinstance(result, dict) and result.get('geographic_plans'))
    if available:
        try:
            view = render_geography(result, month, load_stations(root or PROJECT_ROOT))
        except (OSError, ValueError):
            available = False
            view = {**empty, 'note_md': 'Station coordinates unavailable; the crew and demand charts above remain usable.'}
    valid = view['figure'] is not None
    return (gr.update(value=month if valid else None, interactive=available),
            gr.update(value=view['figure'], visible=valid), view['pool_md'], view['note_md'])


def _outputs(state, root=None):
    legacy=_legacy_outputs(state)
    view=render_result(state.get('result'))
    extra=[_extraction_cards(state,root),view['kpi_html'],
           gr.update(value=view['crew_figure'],visible=view['crew_figure'] is not None),
           gr.update(value=view['demand_figure'],visible=view['demand_figure'] is not None),
           view['annual_table'],view['backtest_table'],view['monthly_table'],view['explanation_md'],
           *_geographic_outputs(state,root=root)]
    return (*legacy,*extra)


def _with_form(state, root=None):
    original = state.get('original_llm') or {}
    return (*_outputs(state,root), original.get('start_date') or '', original.get('end_date') or '',
            original.get('city') or '', original.get('location') or '', '' if original.get('expected_crowd_size') is None else str(original['expected_crowd_size']),
            '\n'.join(original.get('ambiguities') or []), '')


class ScreenActions:
    """Thin callbacks, also exercised through Gradio's local HTTP client."""
    def __init__(self, service): self.service = service

    def _out(self, state): return _outputs(state, self.service.root)

    def _form(self, state): return _with_form(state, self.service.root)

    def geography(self, state, month):
        return _geographic_outputs(state, month, self.service.root)

    def select(self, event_id):
        state = self.service.select(event_id)
        doc = state.get('document') or {}
        return (doc.get('source_title',''),doc.get('source_url',''),doc.get('source_text',''),*self._form(state))

    def input_changed(self, state, title, url, text):
        return self._form(self.service.invalidate(state,_document(state,title,url,text)))

    def saved(self, state, title, url, text):
        return self._form(self.service.load_saved(state,_document(state,title,url,text)))

    def live(self, state, title, url, text):
        return self._form(self.service.extract_live(state,_document(state,title,url,text)))

    def review_changed(self, state):
        return self._out(self.service.invalidate_review(state))

    def scenario_changed(self, state):
        updated = copy.deepcopy(state)
        updated['result'] = None
        if updated.get('review_digest'):
            updated.update(status='review_confirmed',error=None)
        return self._out(updated)

    def confirm(self, state, title, url, text, start, end, city, location, crowd, ambiguities, notes):
        document = _document(state,title,url,text)
        current = self.service.invalidate(state,document)
        return self._out(self.service.confirm(current,document,
                                             _edits(start,end,city,location,crowd,ambiguities),_text(notes)))

    def apply(self, state, title, url, text, start, end, city, location, crowd, ambiguities, notes, increment, conversion):
        document = _document(state,title,url,text)
        current = self.service.invalidate(state,document)
        return self._out(self.service.apply(current,document,
                                           _edits(start,end,city,location,crowd,ambiguities),_text(notes),
                                           increment=increment,conversion=conversion))


def create_app(root=None, *, service=None):
    """Build the one-screen workflow; calculations and review gates stay intact."""
    root=Path(root or PROJECT_ROOT)
    service=service or AppService(root)
    actions=ScreenActions(service)
    choices=service.choices()
    initial=service.select(choices[0][1])
    doc=initial['document']; values=_with_form(initial,root); form=values[-7:]
    with gr.Blocks(title='From Event Headlines to Crew Decisions',analytics_enabled=False) as app:
        gr.Markdown('# From Event Headlines to Crew Decisions')
        gr.HTML(executive_summary(pd.read_csv(root / 'results/focused_event_chain.csv')),css_template=APP_CSS)
        gr.HTML(_diagram_html(root),css_template=APP_CSS)
        state=gr.State(initial)
        gr.Markdown('## 1. Choose an event announcement')
        event=gr.Dropdown(choices=choices,value=choices[0][1],label='Event source')
        with gr.Row():
            with gr.Column(min_width=320):
                gr.Markdown('### Read the original')
                title=gr.Textbox(value=doc['source_title'],label='Source title')
                url=gr.Textbox(value=doc['source_url'],label='Source URL')
                text=gr.Textbox(value=doc['source_text'],label='Original source excerpt',lines=6)
                with gr.Row():
                    saved=gr.Button('Load saved real response')
                    live=gr.Button('Extract with OpenAI')
                gr.Markdown('Saved results require the exact source and input. The live button alone makes a new API call; failures do not fall back silently.')
            with gr.Column(min_width=320):
                gr.Markdown('### 2. See what OpenAI extracted')
                status=gr.Markdown(values[1])
                extraction=gr.HTML(value=values[9],label='Readable extraction',css_template=APP_CSS)
                with gr.Accordion('Raw response, model and validation details',open=False):
                    original=gr.JSON(value=values[2],label='Unedited LLM output: dates, city, location, crowd and ambiguities')
                    provenance=gr.JSON(value=values[3],label='API provenance (no credentials)')
                    gr.Markdown('Saved mode replays an actual recorded API response; it does not run a new model. Schema and literal-evidence checks do not establish semantic truth. Existing review flags are shown only for matching saved source/output evidence.')
        gr.Markdown('## 3. Confirm or correct the facts\nYour fields below are separate from the original model output. Keep unknowns blank; check participants versus spectators and unsupported dates. Nothing reaches the plan automatically.')
        with gr.Row():
            start=gr.Textbox(value=form[0],label='Start date (YYYY-MM-DD)',min_width=180)
            end=gr.Textbox(value=form[1],label='End date (YYYY-MM-DD)',min_width=180)
            city=gr.Textbox(value=form[2],label='City / municipality',min_width=180)
        with gr.Row():
            location=gr.Textbox(value=form[3],label='Venue or location',min_width=220)
            crowd=gr.Textbox(value=form[4],label='Spectators (blank = unknown)',min_width=220)
        ambiguities=gr.Textbox(value=form[5],label='Ambiguities to retain (one per line)',lines=2)
        notes=gr.Textbox(value='',label='Confirmation note (required for corrections)',lines=2)
        confirm=gr.Button('Confirm reviewed values (this session only)')
        gr.Markdown('Confirmation applies only to this scenario session. The saved model response and separate evaluation records remain unchanged.')
        with gr.Accordion('Inspect the session-confirmed values',open=False):
            reviewed=gr.JSON(value=None,label='Session-confirmed record (separate from original LLM output)')
        gr.Markdown('## 4. Explore an explicit demand scenario\nThe increment is **your uncalibrated scenario assumption**, not demand estimated by OpenAI or a measured event effect. Comparisons are **retrospective scenarios**, not proof of forecast improvement.')
        increment=gr.Number(value=3000,minimum=0,label='Added handling actions for this event (user assumption)')
        with gr.Accordion('Capacity and handling-unit assumptions',open=False):
            gr.Markdown('Nominal capacity stays **120 bikes/shift, 6 shifts/week**, prorated by calendar days / 7. A pickup and a delivery are two handling actions. Pairing them as one course bike is a conditional convention; unbalanced depot work cannot automatically be halved.')
            conversion=gr.Radio(choices=[('1 handling action per course bike',1),('2 handling actions per course bike (pairing assumption)',2)],value=1,label='Handling actions per course bike')
        apply=gr.Button('Apply to plan',variant='primary',interactive=False)
        gr.Markdown('## 5. Compare crew decisions\nCards and charts use the frozen 2026 forecast plus your scenario increment, for the selected city or staffing group. Held-out evaluation is in a separate tab. Before/after means **no event increment -> reviewed event scenario**. The no-event baseline is an optimized model plan, not observed Bluebikes staffing. Initial crews are course-provided starting conditions, not an audited current deployment.')
        kpis=gr.HTML(value='',label='Event-month decisions',css_template=APP_CSS)
        crew_plot=gr.Plot(value=None,label='Monthly crew plan',visible=False,elem_classes=['bb-chart'])
        demand_plot=gr.Plot(value=None,label='Demand and capacity',visible=False,elem_classes=['bb-chart'])
        interpretation=gr.Markdown('')
        gr.Markdown('### Geographic crew comparison\nOffline station-coordinate view of the same computed plans. One month controls both panels; the event-month KPI above is unchanged by this selector. No map tiles, event-location markers or station-level demand estimates are used.')
        map_month=gr.Dropdown(choices=MAP_MONTHS,value=None,label='Map month (both panels)',interactive=False)
        geographic_plot=gr.Plot(value=None,label='City crews by station coordinates',show_label=False,visible=False,elem_classes=['bb-chart','bb-geo-chart'])
        pool=gr.Markdown('')
        geographic_note=gr.Markdown('')
        with gr.Accordion('Detailed totals and monthly plan',open=False):
            with gr.Tabs():
                with gr.Tab('Jan-Dec forecast - all cities'):
                    gr.Markdown('All-city **2026 annual forecast**: twelve-month cash cost and forecast-proxy shortfall. Mandatory 2027 seasonal cost is separate.')
                    annual=gr.Dataframe(value=pd.DataFrame(),label='All-city annual forecast',interactive=False,wrap=False,elem_classes=['bb-detail-table'])
                with gr.Tab('Jan-Sep backtest - all cities'):
                    gr.Markdown('All-city **held-out Jan-Sep 2026 evaluation**: nine-month cash cost and observed-trip-derived proxy shortfall. The scenario remains retrospective; this is not an event-forecast improvement claim.')
                    backtest=gr.Dataframe(value=pd.DataFrame(),label='All-city held-out backtest',interactive=False,wrap=False,elem_classes=['bb-detail-table'])
                with gr.Tab('Selected group - monthly'):
                    monthly=gr.Dataframe(value=pd.DataFrame(),label='Monthly group details',interactive=False,wrap=False,elem_classes=['bb-detail-table'])
        # These hidden components retain the original local API response contract.
        comparison=gr.Dataframe(value=pd.DataFrame(),label='Legacy same-period data',interactive=False,visible=False)
        chain=gr.Dataframe(value=pd.DataFrame(),label='Legacy group data',interactive=False,visible=False)
        result_notes=gr.Markdown('',visible=False)
        out=[state,status,original,provenance,reviewed,apply,comparison,chain,result_notes,
             extraction,kpis,crew_plot,demand_plot,annual,backtest,monthly,interpretation,
             map_month,geographic_plot,pool,geographic_note]
        form_out=out+[start,end,city,location,crowd,ambiguities,notes]
        doc_inputs=[state,title,url,text]
        review_inputs=doc_inputs+[start,end,city,location,crowd,ambiguities,notes]
        options=dict(concurrency_id='event-workflow',concurrency_limit=1)
        event.change(actions.select,event,[title,url,text]+form_out,api_name='select_event',show_progress='hidden',**options)
        for component in [title,url,text]:
            component.input(actions.input_changed,doc_inputs,form_out,api_name=None,api_visibility='private',show_progress='hidden',**options)
        saved.click(actions.saved,doc_inputs,form_out,api_name='load_saved',show_progress='hidden',**options)
        live.click(actions.live,doc_inputs,form_out,api_name='extract_live',show_progress='minimal',**options)
        for component in [start,end,city,location,crowd,ambiguities,notes]:
            component.input(actions.review_changed,state,out,api_name=None,api_visibility='private',show_progress='hidden',**options)
        for component in [increment,conversion]:
            component.input(actions.scenario_changed,state,out,api_name=None,api_visibility='private',show_progress='hidden',**options)
        confirm.click(actions.confirm,review_inputs,out,api_name='confirm_review',show_progress='hidden',**options)
        apply.click(actions.apply,review_inputs+[increment,conversion],out,api_name='apply_plan',show_progress='minimal',**options)
        map_month.input(actions.geography,[state,map_month],[map_month,geographic_plot,pool,geographic_note],api_name='geographic_month',show_progress='hidden',**options)
    app.queue(default_concurrency_limit=1)
    return app


def launch_local(root=None, *, port=7860, inline=False, prevent_thread_lock=False):
    """Bind loopback only; no deployment, tunnel, automatic browser or analytics."""
    if not isinstance(port,int) or isinstance(port,bool) or not 1024 <= port <= 65535:
        raise ValueError('Choose a local port between 1024 and 65535')
    app = create_app(root)
    app.launch(server_name='127.0.0.1',server_port=port,share=False,inbrowser=False,
               inline=inline,prevent_thread_lock=prevent_thread_lock,show_error=False,
               quiet=True,enable_monitoring=False,footer_links=[],css=APP_CSS)
    return app
