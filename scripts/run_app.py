"""Start the local Bluebikes screen; stop with Ctrl+C."""
from pathlib import Path
import argparse
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bluebikes.app import launch_local

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=7860)
    args=parser.parse_args()
    print(f'Bluebikes local app: http://127.0.0.1:{args.port} ; stop with Ctrl+C',flush=True)
    launch_local(ROOT,port=args.port)
