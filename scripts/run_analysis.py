"""Run after acquire_data.py; recorded replay and fixture mode need no network."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bluebikes.analysis import run_analysis

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--event-mode",choices=["fixture","live","recorded"],default="recorded")
    args=parser.parse_args()
    summary=run_analysis(ROOT,args.event_mode)
    print(json.dumps({k:summary[k] for k in ["artifact_status","selected_model","forecast_backtest","events_status","live_llm_verified"]},indent=2))
