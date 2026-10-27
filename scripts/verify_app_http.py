"""Exercise actual loopback Gradio callbacks; never make a paid API request."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bluebikes.app import APP_CSS, UI_EXTRA_KEYS, create_app
from bluebikes.app_service import AppService
from gradio_client import Client
import pandas as pd


def extras(output, *, selected=False):
    """State/Button are omitted by the HTTP client; seven core outputs stay fixed."""
    body = output[3:] if selected else output
    assert len(body) >= 7 + len(UI_EXTRA_KEYS)
    return dict(zip(UI_EXTRA_KEYS, body[7:7 + len(UI_EXTRA_KEYS)]))


def payload(value):
    return value.get('value') if isinstance(value, dict) and value.get('__type__') == 'update' else value


def frame(value):
    value = payload(value)
    return pd.DataFrame(value.get('data', []), columns=value.get('headers', [])) if value else pd.DataFrame()


def assert_cleared(output, *, extraction=True):
    view = extras(output)
    if extraction:
        assert output[1] is None and view['extraction_html'] == ''
    assert not frame(output[4]).shape[0] and not frame(output[5]).shape[0]
    assert view['kpi_html'] == '' and view['explanation_md'] == ''
    for name in ['crew_figure', 'demand_figure']:
        assert payload(view[name]) is None
        if isinstance(view[name], dict) and 'visible' in view[name]:
            assert view[name]['visible'] is False
    for name in ['annual_table', 'backtest_table', 'monthly_table']:
        assert frame(view[name]).empty


def run():
    baseline = json.loads((ROOT / 'docs/ui-polish-baseline.json').read_text(encoding='utf-8'))
    protected = list(baseline['protected_model_and_evidence_sha256'])
    before = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in protected}
    assert all(before[row['path']] == row['baseline_sha256'] for row in baseline['original_frozen_seven'])
    baseline_differences = {name: {'committed': baseline['protected_model_and_evidence_sha256'][name], 'before_http': digest}
                            for name, digest in before.items() if digest != baseline['protected_model_and_evidence_sha256'][name]}
    for candidate in [7873, 7875]:
        try:
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', candidate))
            port = candidate
            break
        except OSError:
            continue
    else:
        raise RuntimeError('No dedicated HTTP verification port is available')
    guard_patch = patch('bluebikes.app_service.extract_event', side_effect=AssertionError('Unexpected unmocked provider request'))
    unmocked_provider = guard_patch.start()
    app = None
    checks = []
    try:
        service = AppService(ROOT)
        app = create_app(ROOT, service=service)
        app.launch(server_name='127.0.0.1', server_port=port, share=False, inbrowser=False,
                   prevent_thread_lock=True, show_error=False, quiet=True, enable_monitoring=False,
                   footer_links=[], css=APP_CSS)
        client = Client(f'http://127.0.0.1:{port}', verbose=False)

        def invoke(*args, api_name):
            return client.submit(*args, api_name=api_name).result(timeout=60)

        selected = invoke(service.choices()[0][1], api_name='/select_event')
        assert selected[4]['city'] == 'Boston' and selected[4]['expected_crowd_size'] is None
        assert 'Saved real' in selected[3] and selected[5]['mode'] == 'recorded'
        assert selected[-3] == ''  # Last seven outputs are always the editable form.
        card = extras(selected, selected=True)['extraction_html']
        assert 'Not stated' in card and 'Athlete or participant counts are not used' in card
        checks.append('saved actual response has a readable unknown crowd; athlete count is not presented as audience')
        form = list(selected[:3]) + list(selected[-7:])
        blocked = invoke(*form, 3000, 1, api_name='/apply_plan')
        assert 'Confirm' in blocked[0]
        assert_cleared(blocked, extraction=False)
        checks.append('unconfirmed Apply is blocked and leaves no old chart, KPI or period table')
        confirmed = invoke(*form, api_name='/confirm_review')
        assert confirmed[3]['city'] == 'Boston'
        applied = invoke(*form, 3000, 1, api_name='/apply_plan')
        table = frame(applied[4])
        assert len(table) == 4 and set(table['Scenario']) == {'No-event baseline', 'Reviewed event'}
        observed = table[table['Period'] == 'Jan-Sep 2026 observed proxy']
        assert set(observed['Cash cost ($)']) == {1342800, 1339800}
        chain = frame(applied[5])
        april = chain[chain.Month == 4].iloc[0]
        assert (april['FT baseline'], april['FT event']) == (12, 13)
        assert '2026-03' in applied[6] and '3 -> 4' in applied[6]
        view = extras(applied)
        assert 'April 2026' in view['kpi_html'] and 'March 2026' in view['kpi_html']
        plots = {name: payload(view[name]) for name in ['crew_figure', 'demand_figure']}
        assert all(isinstance(value, dict) and value.get('plot') for value in plots.values())
        annual, heldout = frame(view['annual_table']), frame(view['backtest_table'])
        for visible, period in [(annual, 'Jan-Dec 2026 forecast'), (heldout, 'Jan-Sep 2026 observed proxy')]:
            for raw_label, display_label in [('No-event baseline', 'No event increment'), ('Reviewed event', 'Reviewed event scenario')]:
                expected = table[(table.Scenario == raw_label) & (table.Period == period)]['Cash cost ($)'].iloc[0]
                actual = visible[visible.Plan == display_label]['Cash cost'].iloc[0]
                assert actual == '$' + format(expected, ',.0f')
        assert 'forecast' in view['explanation_md'] and 'observed-proxy' in view['explanation_md']
        checks.append('real cached planning yields April FT12->13 and March hires3->4, two charts and event-month KPI')
        checks.append('visible annual and Jan-Sep tables match their own cost horizons; no mixed-period totals')
        stale = list(form)
        stale[2] += ' changed'
        invalid = invoke(*stale, 3000, 1, api_name='/apply_plan')
        assert_cleared(invalid)
        checks.append('changed source clears extraction cards, both plots, KPI and all tables even when input listener is skipped')
        failed_saved = invoke(*stale[:3], api_name='/load_saved')
        assert 'No exact saved' in failed_saved[0]
        assert_cleared(failed_saved)
        checks.append('edited input cannot reuse unmatched saved evidence')
        invoke(service.choices()[0][1], api_name='/select_event')
        with patch('bluebikes.app_service._project_env', return_value={}), patch('bluebikes.app_service.extract_event') as adapter:
            missing = invoke(*form[:3], api_name='/extract_live')
            adapter.assert_not_called()
        assert 'no configured' in missing[0]
        assert_cleared(missing)
        checks.append('missing project key blocks explicit live action without saved fallback')
        invoke(*form[:3], api_name='/load_saved')
        sentinel = 'synthetic_error_details_must_not_be_shown'
        with patch('bluebikes.app_service._project_env', return_value={'OPENAI_API_KEY': 'HTTP_TEST_NOT_A_SECRET'}), \
                patch('bluebikes.app_service.extract_event', side_effect=RuntimeError(sentinel)) as adapter:
            failed = invoke(*form[:3], api_name='/extract_live')
            assert adapter.call_count == 1
        assert sentinel not in str(failed)
        assert_cleared(failed)
        checks.append('mock live error through HTTP is redacted and clears presentation without fallback')
        recovered = invoke(*form[:3], api_name='/load_saved')
        assert recovered[1]['city'] == 'Boston'
        checks.append('explicit saved reload recovers the readable extraction after live failure')
        participant = next(value for _, value in service.choices() if 'participants_only' in value)
        failure_case = invoke(participant, api_name='/select_event')
        assert failure_case[4]['expected_crowd_size'] == 30000
        failure_card = extras(failure_case, selected=True)['extraction_html']
        assert 'flagged participant count, not verified spectators' in failure_card
        assert 'unsupported inferred date' in failure_card
        assert failure_case[6] is None and frame(failure_case[7]).empty
        corrected = list(failure_case[:3]) + list(failure_case[-7:])
        corrected[3] = ''
        corrected[4] = ''
        corrected[7] = ''
        corrected[-1] = 'Demo correction: source gives participants, no spectator estimate or event day. Unknown dates remain null.'
        reviewed = invoke(*corrected, api_name='/confirm_review')
        assert reviewed[3]['start_date'] is None and reviewed[3]['expected_crowd_size'] is None
        refused = invoke(*corrected, 3000, 1, api_name='/apply_plan')
        assert frame(refused[4]).empty and refused[3] is None
        assert extras(refused)['kpi_html'] == ''
        checks.append('actual participant/date error is visibly flagged; corrected unknown dates prevent planning')
        snapshots = {'same_period_comparison': json.loads(table.to_json(orient='records')),
                     'visible_annual_table': json.loads(annual.to_json(orient='records')),
                     'visible_backtest_table': json.loads(heldout.to_json(orient='records')),
                     'april_row': json.loads(april.to_json()),
                     'plot_types': {name: value.get('type') for name, value in plots.items()}}
        unmocked_provider.assert_not_called()
    finally:
        if app is not None:
            app.close()
        guard_patch.stop()
    with socket.socket() as sock:
        stopped = sock.connect_ex(('127.0.0.1', port)) != 0
    assert stopped
    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest for name, digest in before.items())
    report = {'verified_utc': datetime.now(timezone.utc).isoformat(), 'local_port': port, 'share': False,
              'checks': checks, 'checks_passed': len(checks), 'real_api_calls': 0,
              'live_error_test': 'Mocked adapter failure through actual Gradio HTTP, not a real provider outage',
              'recorded_outputs': 'Genuine saved OpenAI responses, not fixtures',
              'server_closed_and_port_released': stopped, 'protected_artifact_hashes_unchanged': before,
              'ui_polish_baseline_commit': baseline['baseline_commit'],
              'baseline_differences_already_present_before_http': baseline_differences,
              'human_evaluation_files_updated': False, 'snapshots': snapshots}
    (ROOT / 'docs/verification-gradio-http.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    print(f'PASS: {len(checks)} actual local HTTP checks; zero real API calls; server closed.')


if __name__ == '__main__':
    run()
