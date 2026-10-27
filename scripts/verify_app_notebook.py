"""Execute the actual optional app cell in a real Notebook kernel, then close it.

Only the launch flag and local port are changed. No full analysis, package install,
live extraction, frozen artifact write, or public share link is requested.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import runpy
import socket
import sys

import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "BLUEBIKES_NOTEBOOK_SMOKE_JSON="
PROTECTED = [
    "fixtures/event_documents.json", "fixtures/event_documents_additional.json",
    "prompts/event_extraction_v1.txt", "prompts/event_schema.json",
    "results/event_extraction_live.json", "results/event_extraction_evaluation.json",
    "results/event_extraction_additional_live.json", "results/event_extraction_additional_evaluation.json",
    "results/event_original_four_human_review.csv", "results/event_extraction_additional_review.csv",
]


def port_listening(port):
    with socket.socket() as connection:
        connection.settimeout(0.3)
        return connection.connect_ex(("127.0.0.1", port)) == 0


def hashes():
    return {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in PROTECTED}


def run(port=7868, report_output="docs/verification-gradio-notebook.json"):
    started = datetime.now(timezone.utc).isoformat()
    report_path = ROOT / report_output
    target = ROOT / "build/app_notebook_smoke.ipynb"
    if port_listening(port):
        raise RuntimeError(f"Port {port} is already occupied; no existing server was stopped")
    before = hashes()
    builder = ROOT / "scripts/build_demo_notebook.py"
    built = runpy.run_path(str(builder))["build"]()
    candidates = [cell.source for cell in built.cells if cell.cell_type == "code"
                  and "LAUNCH_LOCAL_APP = False" in cell.source and "launch_local(" in cell.source]
    if len(candidates) != 1:
        raise AssertionError("Expected exactly one actual optional app cell")
    original = candidates[0]
    launched = original.replace("LAUNCH_LOCAL_APP = False", "LAUNCH_LOCAL_APP = True", 1)
    launched = launched.replace("LOCAL_APP_PORT = 7860", f"LOCAL_APP_PORT = {port}", 1)
    if (launched.replace("LAUNCH_LOCAL_APP = True", "LAUNCH_LOCAL_APP = False", 1)
            .replace(f"LOCAL_APP_PORT = {port}", "LOCAL_APP_PORT = 7860", 1)) != original:
        raise AssertionError("Optional cell changed beyond its flag and port")
    # Source currently assigns the real launched Blocks handle to app. Fail if
    # that builder contract changes instead of silently testing another launcher.
    if "app = launch_local(" not in launched:
        raise AssertionError("Inspect the builder's app-handle variable before running this verifier")
    setup = '''from pathlib import Path
import sys, json, socket, time
from urllib.parse import urlparse
import requests
ROOT = Path.cwd()
assert (ROOT / 'bluebikes/app.py').exists()
sys.path.insert(0, str(ROOT))
_NB_OPENAI_ATTEMPTS = []
_NB_ORIGINAL_REQUEST = requests.sessions.Session.request
def _nb_request_guard(self, method, url, *args, **kwargs):
    host = (urlparse(str(url)).hostname or '').lower()
    if host == 'api.openai.com' or host.endswith('.openai.com'):
        _NB_OPENAI_ATTEMPTS.append({'method': str(method), 'host': host})
        raise AssertionError('Unexpected live OpenAI request during Notebook startup')
    return _NB_ORIGINAL_REQUEST(self, method, url, *args, **kwargs)
requests.sessions.Session.request = _nb_request_guard
print('Real Notebook kernel setup; live OpenAI requests are guarded, not made.')
'''
    verify_and_close = '''_nb_result = {
    'port': __PORT__, 'config_http_status': None, 'share': None,
    'analytics_enabled': None, 'server_name': None, 'server_port': None,
    'close_called': False, 'port_released_before_kernel_shutdown': False,
}
_nb_app = globals().get('app')
try:
    assert _nb_app is not None, 'Actual optional launch cell did not return an app handle'
    response = requests.get('http://127.0.0.1:__PORT__/config', timeout=15)
    _nb_result['config_http_status'] = response.status_code
    response.raise_for_status()
    config = response.json()
    _nb_result['config_component_count'] = len(config.get('components', []))
    _nb_result['config_enable_queue'] = config.get('enable_queue')
    _nb_result['share'] = bool(_nb_app.share)
    _nb_result['analytics_enabled'] = bool(_nb_app.analytics_enabled)
    _nb_result['server_name'] = _nb_app.server_name
    _nb_result['server_port'] = _nb_app.server_port
    assert _nb_result['config_http_status'] == 200
    assert _nb_result['share'] is False
    assert _nb_result['analytics_enabled'] is False
    assert _nb_result['server_name'] == '127.0.0.1'
    assert _nb_result['server_port'] == __PORT__
    assert not _NB_OPENAI_ATTEMPTS, 'Startup attempted a live extraction'
finally:
    try:
        if _nb_app is not None:
            _nb_app.close()
            _nb_result['close_called'] = True
    finally:
        # Also closes a partially launched Blocks instance if launch raised before
        # its return value could be assigned. This affects this kernel only.
        import gradio as _nb_gradio
        _nb_gradio.close_all(verbose=False)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            with socket.socket() as connection:
                connection.settimeout(0.2)
                available = connection.connect_ex(('127.0.0.1', __PORT__)) != 0
            if available:
                break
            time.sleep(0.1)
        _nb_result['port_released_before_kernel_shutdown'] = available
        _nb_result['openai_adapter_request_attempts'] = len(_NB_OPENAI_ATTEMPTS)
        requests.sessions.Session.request = _NB_ORIGINAL_REQUEST
        print('BLUEBIKES_NOTEBOOK_SMOKE_JSON=' + json.dumps(_nb_result, sort_keys=True))
assert _nb_result['close_called']
assert _nb_result['port_released_before_kernel_shutdown'], 'App port remains bound after app.close()'
assert _nb_result['openai_adapter_request_attempts'] == 0
'''.replace("__PORT__", str(port))
    notebook = nbf.v4.new_notebook(cells=[nbf.v4.new_code_cell(setup), nbf.v4.new_code_cell(launched),
                                       nbf.v4.new_code_cell(verify_and_close)], metadata={
        "kernelspec": {"name": "bluebikes", "display_name": "Bluebikes project Python", "language": "python"}})
    kernel_file = ROOT / "build/kernels/bluebikes/kernel.json"
    kernel = json.loads(kernel_file.read_text(encoding="utf-8-sig"))
    if not Path(kernel["argv"][0]).exists():
        raise RuntimeError("Existing project Notebook kernel executable is missing")
    os.environ["JUPYTER_PATH"] = str(ROOT / "build")
    os.environ["IPYTHONDIR"] = str(ROOT / "build/ipython")
    os.environ["JUPYTER_RUNTIME_DIR"] = str(ROOT / "build/runtime")
    os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
    client = NotebookClient(notebook, timeout=180, kernel_name="bluebikes",
                            resources={"metadata": {"path": str(ROOT)}}, allow_errors=False)
    failure = None
    cleanup_executed = False
    try:
        with client.setup_kernel():
            try:
                client.execute_cell(notebook.cells[0], 0, execution_count=1)
                client.execute_cell(notebook.cells[1], 1, execution_count=2)
            finally:
                # Attempt cleanup even if the actual launcher cell failed.
                cleanup_executed = True
                client.execute_cell(notebook.cells[2], 2, execution_count=3)
    except Exception as error:
        failure = {"type": type(error).__name__, "message": str(error)[-2500:]}
    finally:
        target.parent.mkdir(exist_ok=True)
        nbf.write(notebook, target)
        after = hashes()
        detail = None
        for cell in notebook.cells:
            for output in cell.get("outputs", []):
                for line in output.get("text", "").splitlines():
                    if line.startswith(PREFIX):
                        detail = json.loads(line[len(PREFIX):])
        errors = [{"cell": i + 1, "ename": output.get("ename"), "evalue": output.get("evalue")}
                  for i, cell in enumerate(notebook.cells) for output in cell.get("outputs", [])
                  if output.get("output_type") == "error"]
        unchanged = before == after
        released_after_shutdown = not port_listening(port)
        passed = (failure is None and not errors and detail is not None
                  and detail.get("port_released_before_kernel_shutdown") is True
                  and detail.get("openai_adapter_request_attempts") == 0
                  and unchanged and released_after_shutdown)
        report = {
            "status": "passed" if passed else "failed", "executed_utc": started,
            "command": ".venv/Scripts/python.exe -B scripts/verify_app_notebook.py --port " + str(port) + " --output " + report_output,
            "kernel_executable": kernel["argv"][0], "kernel_name": "bluebikes",
            "source_builder": "scripts/build_demo_notebook.py", "source_cell_sha256": sha256(original.encode()).hexdigest(),
            "executed_cell_sha256": sha256(launched.encode()).hexdigest(),
            "only_cell_changes": {"LAUNCH_LOCAL_APP": [False, True], "LOCAL_APP_PORT": [7860, port]},
            "notebook_artifact": "build/app_notebook_smoke.ipynb (ignored)", "code_cells": 3,
            "execution_counts": [cell.get("execution_count") for cell in notebook.cells],
            "cell_errors": errors, "cleanup_cell_attempted_in_finally": cleanup_executed,
            "actual_launch_and_close": detail, "port_released_after_kernel_shutdown": released_after_shutdown,
            "new_live_llm_api_calls": 0 if detail and detail.get("openai_adapter_request_attempts") == 0 else None,
            "guard_scope": "The requests-based OpenAI adapter endpoint is blocked/recorded if unexpectedly invoked; local config GET is real HTTP",
            "preserved_artifact_hashes_unchanged": unchanged, "preserved_artifacts": before,
            "failure": failure,
        }
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({"status": report["status"], "execution_counts": report["execution_counts"],
                          "cell_errors": len(errors), "actual_launch_and_close": detail,
                          "port_released_after_kernel_shutdown": released_after_shutdown,
                          "preserved_artifact_hashes_unchanged": unchanged}, indent=2))
    if report["status"] != "passed":
        raise RuntimeError("Notebook app verification failed; inspect docs/verification-gradio-notebook.json")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7868)
    parser.add_argument("--output", default="docs/verification-gradio-notebook.json")
    arguments = parser.parse_args()
    run(arguments.port, arguments.output)
