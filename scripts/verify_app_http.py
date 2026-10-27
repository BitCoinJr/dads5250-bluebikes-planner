"""Exercise the actual local Gradio HTTP workflow without paid API calls."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import socket
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bluebikes.app import create_app
from bluebikes.app_service import AppService
from gradio_client import Client
import pandas as pd


def run():
    protected=['fixtures/event_documents.json','prompts/event_extraction_v1.txt','prompts/event_schema.json',
               'results/event_extraction_live.json','results/event_extraction_evaluation.json',
               'results/event_extraction_additional_live.json','results/event_extraction_additional_evaluation.json',
               'results/event_original_four_human_review.csv','results/event_extraction_additional_review.csv']
    before={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in protected}
    for candidate in range(7861,7870):
        try:
            with socket.socket() as sock: sock.bind(('127.0.0.1',candidate))
            port=candidate; break
        except OSError: continue
    else: raise RuntimeError('No verification port available')
    service=AppService(ROOT)
    app=create_app(ROOT,service=service)
    checks=[]
    try:
        app.launch(server_name='127.0.0.1',server_port=port,share=False,inbrowser=False,
                   prevent_thread_lock=True,show_error=False,quiet=True,enable_monitoring=False,footer_links=[])
        client=Client(f'http://127.0.0.1:{port}',verbose=False)
        def invoke(*args,api_name):
            return client.submit(*args,api_name=api_name).result(timeout=45)
        selected=invoke(service.choices()[0][1],api_name='/select_event')
        assert selected[4]['city']=='Boston' and selected[4]['expected_crowd_size'] is None
        assert 'Saved real' in selected[3] and selected[5]['mode']=='recorded'
        assert selected[14]==''  # Gradio's HTTP client omits State and Button outputs
        checks.append('saved actual response loaded with null crowd and no session confirmation')
        form=list(selected[:3])+list(selected[10:17])
        blocked=invoke(*form,3000,1,api_name='/apply_plan')
        assert 'Confirm' in blocked[0] and not blocked[4]['data']
        checks.append('unconfirmed Apply blocked by actual HTTP endpoint')
        confirmed=invoke(*form,api_name='/confirm_review')
        assert confirmed[3]['city']=='Boston'
        applied=invoke(*form,3000,1,api_name='/apply_plan')
        table=pd.DataFrame(applied[4]['data'],columns=applied[4]['headers'])
        assert len(table)==4 and set(table['Scenario'])=={'No-event baseline','Reviewed event'}
        observed=table[table['Period']=='Jan-Sep 2026 observed proxy']
        assert set(observed['Cash cost ($)'])=={1342800,1339800}
        chain=pd.DataFrame(applied[5]['data'],columns=applied[5]['headers'])
        april=chain[chain.Month==4].iloc[0]
        assert (april['FT baseline'],april['FT event'])==(12,13)
        assert '2026-03' in applied[6] and '3 -> 4' in applied[6]
        checks.append('confirmed event replans to April FT12->13 and March hires3->4; matching cost/shortfall periods')
        stale=list(form); stale[2]+=' changed'
        invalid=invoke(*stale,3000,1,api_name='/apply_plan')
        assert invalid[1] is None and not invalid[4]['data']
        checks.append('changed source rejects old extraction/confirmation/plan even when client skips input listener')
        failed_saved=invoke(*stale[:3],api_name='/load_saved')
        assert failed_saved[1] is None and 'No exact saved' in failed_saved[0]
        checks.append('edited input cannot reuse an unmatched saved response')
        invoke(service.choices()[0][1],api_name='/select_event')
        with patch('bluebikes.app_service._project_env',return_value={}), patch('bluebikes.app_service.extract_event') as adapter:
            missing=invoke(*form[:3],api_name='/extract_live')
            adapter.assert_not_called()
        assert missing[1] is None and 'no configured' in missing[0] and not missing[4]['data']
        checks.append('missing project key visibly blocks live extraction with no implicit saved fallback')
        invoke(*form[:3],api_name='/load_saved')
        sentinel='synthetic_error_details_must_not_be_shown'
        with patch('bluebikes.app_service._project_env',return_value={'OPENAI_API_KEY':'HTTP_TEST_NOT_A_SECRET'}), patch('bluebikes.app_service.extract_event',side_effect=RuntimeError(sentinel)) as adapter:
            failed=invoke(*form[:3],api_name='/extract_live')
            assert adapter.call_count==1
        assert failed[1] is None and not failed[4]['data'] and sentinel not in str(failed)
        checks.append('mock API error is redacted and clears outputs without fallback')
        recovered=invoke(*form[:3],api_name='/load_saved')
        assert recovered[1]['city']=='Boston'
        checks.append('explicit saved reload recovers demo after live failure')
        participant=next(v for label,v in service.choices() if 'participants_only' in v)
        failure_case=invoke(participant,api_name='/select_event')
        assert failure_case[4]['expected_crowd_size']==30000
        assert failure_case[6] is None and not failure_case[7]['data']
        corrected=list(failure_case[:3])+list(failure_case[10:17])
        corrected[3]=''; corrected[4]=''; corrected[7]=''
        corrected[-1]='Demo correction: source gives participants, no spectator estimate or event day. Unknown dates remain null.'
        reviewed=invoke(*corrected,api_name='/confirm_review')
        assert reviewed[3]['start_date'] is None and reviewed[3]['expected_crowd_size'] is None
        refused=invoke(*corrected,3000,1,api_name='/apply_plan')
        assert not refused[4]['data'] and refused[3] is None
        checks.append('actual participant/date failure remains visible; corrected unknowns block planning')
        snapshots={'same_period_comparison':json.loads(table.to_json(orient='records')),'april_row':json.loads(april.to_json())}
    finally:
        app.close()
    with socket.socket() as sock:
        stopped=sock.connect_ex(('127.0.0.1',port))!=0
    assert stopped
    assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==v for n,v in before.items())
    report={'verified_utc':datetime.now(timezone.utc).isoformat(),'local_port':port,'share':False,
            'checks':checks,'checks_passed':len(checks),'real_api_calls':0,
            'live_error_test':'mocked adapter failure through actual Gradio HTTP endpoint, not a real provider outage',
            'recorded_outputs':'genuine saved OpenAI responses, not fixtures',
            'server_closed_and_port_released':stopped,'protected_artifact_hashes_unchanged':before,
            'human_evaluation_files_updated':False,'snapshots':snapshots}
    (ROOT/'docs/verification-gradio-http.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    print(f'PASS: {len(checks)} real local HTTP workflow checks; no actual API calls; server closed.')


if __name__=='__main__':run()
