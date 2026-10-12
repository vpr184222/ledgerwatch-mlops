"""CLI job suitable for a scheduler; posts the same validated, atomic batch API used by the UI."""
import argparse
import json
import os
from pathlib import Path
import httpx
parser = argparse.ArgumentParser()
parser.add_argument('csv',type=Path)
parser.add_argument('--url',default='http://localhost:8000')
args = parser.parse_args()
with args.csv.open('rb') as file:
    r = httpx.post(args.url+'/batch',headers={'Authorization':'Bearer '+os.getenv('API_TOKEN','demo-ledger-token')},files={'file':(args.csv.name,file,'text/csv')},timeout=60)
if r.is_error:
    raise SystemExit(f'Batch rejected ({r.status_code}): {r.text}')
print(json.dumps(r.json(),indent=2))
