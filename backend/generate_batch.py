import argparse
from pathlib import Path
from app.data import generate,FEATURES
parser = argparse.ArgumentParser(description='Generate synthetic CSV for batch scoring')
parser.add_argument('--drift',action='store_true')
parser.add_argument('--seed',type=int,default=99)
parser.add_argument('--rows',type=int,default=100)
parser.add_argument('--output',default='runtime/batch.csv')
args = parser.parse_args()
if not 1<=args.rows<=1000:
    parser.error('--rows must be between 1 and 1000')
output = Path(args.output)
output.parent.mkdir(parents=True,exist_ok=True)
generate(args.rows,args.seed,args.drift)[['transaction_id',*FEATURES]].to_csv(output,index=False)
print(output)
