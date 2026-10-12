import argparse
import json
from pathlib import Path
from app.model import train,promote

parser = argparse.ArgumentParser(description='Train or promote a local LedgerWatch model version')
parser.add_argument('--seed',type=int,default=42)
parser.add_argument('--track',action='store_true',help='Log artifacts and metrics to MLflow')
parser.add_argument('--candidate',action='store_true',help='Train without activating; review metrics before promotion')
parser.add_argument('--promote',help='Activate an existing version; also supports rollback')
parser.add_argument('--registry',default='runtime/models')
args = parser.parse_args()
if args.promote:
    promote(Path(args.registry),args.promote)
    print('Activated '+args.promote)
else:
    print(json.dumps(train(Path(args.registry),args.seed,args.track,not args.candidate),indent=2))
