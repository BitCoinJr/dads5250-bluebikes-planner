
"""Regression through actual Gradio HTTP endpoints; no new OpenAI requests."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bluebikes.app import APP_CSS, create_app
from bluebikes.app_service import AppService
from gradio_client import Client
from verify_app_http import assert_cleared, extras, frame

def run():
    checks = []
    service = AppService(ROOT)
    app = create_app(ROOT, service=service)
    with patch("bluebikes.app_service.extract_event", side_effect=AssertionError("No provider calls")) as api:
        try:
            app.launch(server_name="127.0.0.1", server_port=7878, share=False,
                       prevent_thread_lock=True, inbrowser=False, quiet=True, show_error=False,
                       enable_monitoring=False, footer_links=[], css=APP_CSS)
            client = Client("http://127.0.0.1:7878", verbose=False)
            def invoke(*args, api_name):
                return client.submit(*args, api_name=api_name).result(timeout=60)
            for label, source_id in service.choices():
                if not label.startswith("[supplemental]"):
                    continue
                selected = invoke(source_id, api_name="/select_event")
                form = list(selected[:3]) + list(selected[-7:])
                form[3:6] = ["2026-04-21", "2026-04-21", "Boston"]
                form[7] = "30000"
                form[8] = "Edited ambiguity text cannot authorize evaluation data."
                form[9] = "Synthetic regression only: edited facts and notes."
                confirmed = invoke(*form, api_name="/confirm_review")
                assert "Reviewed for this session" in confirmed[0]
                assert "Evaluation only" in confirmed[0]
                with patch.object(service, "_plan") as planner:
                    denied = invoke(*form, 3000, 1, api_name="/apply_plan")
                    planner.assert_not_called()
                assert "Evaluation only" in denied[0]
                assert_cleared(denied, extraction=False)
                assert "Human adjudication" in extras(denied)["extraction_html"]
                checks.append({"check": "edited_and_confirmed_evaluation_case_denied", "source_id": source_id})

            selected = invoke("boston_marathon_2026", api_name="/select_event")
            form = list(selected[:3]) + list(selected[-7:])
            invoke(*form, api_name="/confirm_review")
            applied = invoke(*form, 3000, 1, api_name="/apply_plan")
            april = frame(applied[5]).query("Month == 4").iloc[0]
            assert (april["FT baseline"], april["FT event"]) == (12, 13)
            assert (april["Cost baseline ($)"], april["Cost event ($)"]) == (72000, 78000)
            assert "March 2026" in extras(applied)["kpi_html"]
            checks.append({"check": "original_marathon", "april_ft": [12, 13],
                           "april_cash": [72000, 78000], "hiring_decision": "2026-03"})
            zero = invoke(*form, 0, 1, api_name="/apply_plan")
            for _, row in frame(zero[5]).iterrows():
                for base, event in [("FT baseline", "FT event"), ("Seasonal baseline", "Seasonal event"),
                                    ("Cost baseline ($)", "Cost event ($)"),
                                    ("Uncovered baseline actions", "Uncovered event actions")]:
                    assert row[base] == row[event]
            checks.append({"check": "zero_increment_matches_baseline_all_twelve_months"})
            stale = form.copy()
            stale[2] += " Changed input."
            cleared = invoke(*stale, 3000, 1, api_name="/apply_plan")
            assert_cleared(cleared)
            checks.append({"check": "source_change_clears_all_results_even_without_input_listener"})
            api.assert_not_called()
            output = {"verified_at_utc": datetime.now(timezone.utc).isoformat(),
                      "base_commit": "691ef6a003fe5616cfc2a0afb3de80bfe0372d96",
                      "checks": checks, "new_real_api_calls": 0, "http_port": 7878,
                      "status": "passed", "server_closed_after_checks": True}
            (ROOT / "docs/verification-evaluation-gate-http.json").write_text(
                json.dumps(output, indent=2) + "\n", encoding="utf-8", newline="\n")
            print(f"Passed {len(checks)} HTTP checks; zero provider calls.", flush=True)
        finally:
            app.close()

if __name__ == "__main__":
    run()
