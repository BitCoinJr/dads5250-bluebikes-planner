"""One local Gradio screen; all extraction/planning rules live in AppService."""
from __future__ import annotations

import copy
import os
from pathlib import Path

# Never create an analytics request or a public tunnel from the local demo.
os.environ['GRADIO_ANALYTICS_ENABLED'] = 'False'
import gradio as gr
import pandas as pd

from .app_service import AppService

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAVED_LABEL = '\u4fdd\u5b58\u6e08\u307f\u5b9fAPI\u7d50\u679c / Saved real OpenAI response'
LIVE_LABEL = '\u5b9fAPI\u7d50\u679c / New real OpenAI response'


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


def _outputs(state):
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
            gr.update(interactive=confirmed), comparisons, chain, notes)


def _with_form(state):
    original = state.get('original_llm') or {}
    return (*_outputs(state), original.get('start_date') or '', original.get('end_date') or '',
            original.get('city') or '', original.get('location') or '', '' if original.get('expected_crowd_size') is None else str(original['expected_crowd_size']),
            '\n'.join(original.get('ambiguities') or []), '')


class ScreenActions:
    """Thin callbacks, also exercised through Gradio's local HTTP client."""
    def __init__(self, service): self.service = service

    def select(self, event_id):
        state = self.service.select(event_id)
        doc = state.get('document') or {}
        return (doc.get('source_title',''),doc.get('source_url',''),doc.get('source_text',''),*_with_form(state))

    def input_changed(self, state, title, url, text):
        return _with_form(self.service.invalidate(state,_document(state,title,url,text)))

    def saved(self, state, title, url, text):
        return _with_form(self.service.load_saved(state,_document(state,title,url,text)))

    def live(self, state, title, url, text):
        return _with_form(self.service.extract_live(state,_document(state,title,url,text)))

    def review_changed(self, state):
        return _outputs(self.service.invalidate_review(state))

    def scenario_changed(self, state):
        updated = copy.deepcopy(state)
        updated['result'] = None
        return _outputs(updated)

    def confirm(self, state, title, url, text, start, end, city, location, crowd, ambiguities, notes):
        document = _document(state,title,url,text)
        current = self.service.invalidate(state,document)
        return _outputs(self.service.confirm(current,document,
                                             _edits(start,end,city,location,crowd,ambiguities),_text(notes)))

    def apply(self, state, title, url, text, start, end, city, location, crowd, ambiguities, notes, increment, conversion):
        document = _document(state,title,url,text)
        current = self.service.invalidate(state,document)
        return _outputs(self.service.apply(current,document,
                                           _edits(start,end,city,location,crowd,ambiguities),_text(notes),
                                           increment=increment,conversion=conversion))


def create_app(root=None, *, service=None):
    """Build the same screen for Notebook and standalone local launch."""
    service = service or AppService(root or PROJECT_ROOT)
    actions = ScreenActions(service)
    choices = service.choices()
    initial = service.select(choices[0][1])
    doc = initial['document']
    values = _with_form(initial)
    with gr.Blocks(title='Bluebikes: review an event, then plan', analytics_enabled=False) as app:
        gr.Markdown('# Bluebikes: review an event, then plan\nLocal retrospective scenario. Human confirmation here is **session-only**, not a saved evaluation judgment. TA confirmation, team review, video and submission remain pending.')
        state = gr.State(initial)
        gr.Markdown('## 1. Event and original source')
        event = gr.Dropdown(choices=choices,value=choices[0][1],label='Event excerpt (original four + separate challenge cases)')
        with gr.Row():
            title = gr.Textbox(value=doc['source_title'],label='Source title')
            url = gr.Textbox(value=doc['source_url'],label='Source URL')
        text = gr.Textbox(value=doc['source_text'],label='Original source excerpt (editable; changes invalidate results)',lines=4)
        with gr.Row():
            saved = gr.Button('Load saved real response')
            live = gr.Button('\u5b9fAPI\u3067\u62bd\u51fa / Extract with OpenAI')
        gr.Markdown('Saved mode requires the exact source/title/text and validated request/output hashes. Live extraction occurs **only** when its button is pressed; API failures never silently fall back. A missing key does not prevent saved mode.')
        gr.Markdown('## 2. Extraction: original model output')
        status = gr.Markdown(values[1])
        original = gr.JSON(value=values[2],label='Unedited LLM output: dates, city, location, crowd and ambiguities')
        provenance = gr.JSON(value=values[3],label='API provenance (no credentials)')
        gr.Markdown('## 3. Confirm or correct the values\nCheck spectators versus participants, unsupported dates, city allocation and quantity qualifiers. Blank means unknown. Supply a correction note for manual changes; do not guess missing facts. Nothing is applied automatically.')
        with gr.Row():
            start = gr.Textbox(value=values[9],label='Reviewed start date (YYYY-MM-DD or blank)')
            end = gr.Textbox(value=values[10],label='Reviewed end date (YYYY-MM-DD or blank)')
            city = gr.Textbox(value=values[11],label='Reviewed city (exact municipality or blank)')
        with gr.Row():
            location = gr.Textbox(value=values[12],label='Reviewed location or blank')
            crowd = gr.Textbox(value=values[13],label='Reviewed spectator count (blank = unknown)')
        ambiguities = gr.Textbox(value=values[14],label='Reviewed ambiguities (one per line)',lines=2)
        notes = gr.Textbox(value='',label='Confirmation / correction note (required for edits; optional otherwise)',lines=2)
        confirm = gr.Button('Confirm reviewed values (this session only)')
        reviewed = gr.JSON(value=None,label='Session-confirmed record (separate from original LLM output)')
        gr.Markdown('## 4. Explicitly apply the scenario\n**+3,000 handling actions is uncalibrated**, not LLM-estimated demand or a demonstrated event effect. This is a **retrospective scenario**, not evidence of forecast improvement. Nominal capacity stays **120 bikes/shift, 6 shifts/week**. Two actions per course-bike unit assumes pickup/delivery pairing; it is not measured productivity and can fail for unbalanced depot flows.')
        with gr.Row():
            increment = gr.Number(value=3000,minimum=0,label='Assumed added handling actions for this event')
            conversion = gr.Radio(choices=[('1 handling action per course bike',1),('2 handling actions per course bike (pairing assumption)',2)],value=1,label='Counting convention; 120 bikes/shift stays fixed')
        apply = gr.Button('\u8a08\u753b\u306b\u53cd\u6620 / Apply to plan',variant='primary',interactive=False)
        gr.Markdown('## 5. Baseline versus reviewed-event scenario\nBaseline means the frozen no-event forecast plan. Annual rows pair **Jan-Dec cost with forecast-proxy shortage**; nine-month rows pair **Jan-Sep cost with observed-trip-proxy shortage**. These are not measured lost trips. Mandatory 2027 seasonal costs are separate. Replanning includes earlier hiring/seasonal decisions; it does not imply immediate hiring in the event month.')
        result_notes = gr.Markdown('No plan applied. Confirm the reviewed values, then press Apply to plan.')
        comparison = gr.Dataframe(value=pd.DataFrame(),label='Same-period system comparison',interactive=False,wrap=True)
        chain = gr.Dataframe(value=pd.DataFrame(),label='Selected staffing group by month (forecast proxy shortages)',interactive=False,wrap=True)
        out = [state,status,original,provenance,reviewed,apply,comparison,chain,result_notes]
        form_out = out+[start,end,city,location,crowd,ambiguities,notes]
        doc_inputs = [state,title,url,text]
        review_inputs = doc_inputs+[start,end,city,location,crowd,ambiguities,notes]
        # One workflow queue avoids simultaneous state mutations. Apply still checks
        # current input/edits server-side even if a frontend invalidation was skipped.
        options = dict(concurrency_id='event-workflow',concurrency_limit=1)
        event.change(actions.select,event,[title,url,text]+form_out,api_name='select_event',**options)
        for component in [title,url,text]:
            component.input(actions.input_changed,doc_inputs,form_out,api_name=None,api_visibility='private',**options)
        saved.click(actions.saved,doc_inputs,form_out,api_name='load_saved',**options)
        live.click(actions.live,doc_inputs,form_out,api_name='extract_live',**options)
        for component in [start,end,city,location,crowd,ambiguities,notes]:
            component.input(actions.review_changed,state,out,api_name=None,api_visibility='private',**options)
        for component in [increment,conversion]:
            component.input(actions.scenario_changed,state,out,api_name=None,api_visibility='private',**options)
        confirm.click(actions.confirm,review_inputs,out,api_name='confirm_review',**options)
        apply.click(actions.apply,review_inputs+[increment,conversion],out,api_name='apply_plan',**options)
    app.queue(default_concurrency_limit=1)
    return app


def launch_local(root=None, *, port=7860, inline=False, prevent_thread_lock=False):
    """Bind loopback only; no deployment, tunnel, automatic browser or analytics."""
    if not isinstance(port,int) or isinstance(port,bool) or not 1024 <= port <= 65535:
        raise ValueError('Choose a local port between 1024 and 65535')
    app = create_app(root)
    app.launch(server_name='127.0.0.1',server_port=port,share=False,inbrowser=False,
               inline=inline,prevent_thread_lock=prevent_thread_lock,show_error=False,
               quiet=True,enable_monitoring=False,footer_links=[])
    return app
