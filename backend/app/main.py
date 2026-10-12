import os
import io
import secrets
import sqlite3
import time
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Literal
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, ConfigDict, ValidationError
from .data import FEATURES,generate
from .model import Registry,train,psi
from .store import Store

BASE = Path(__file__).resolve().parents[1]
security = HTTPBearer()

class Transaction(BaseModel):
    model_config = ConfigDict(extra='forbid',allow_inf_nan=False)
    transaction_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    amount: float = Field(gt=0,le=1000000)
    hour: int = Field(ge=0,le=23)
    account_age_days: int = Field(ge=0,le=36500)
    transactions_24h: int = Field(ge=0,le=10000)
    foreign: int = Field(ge=0,le=1)
    distance_km: float = Field(ge=0,le=20000)

class Review(BaseModel):
    status: Literal['investigating','cleared','confirmed']
    reason: str = Field(min_length=5,max_length=500)
    expected_version: int = Field(ge=0)

def create_app(runtime=None,seed_demo=True):
    runtime = Path(runtime or os.getenv('RUNTIME_DIR',str(BASE/'runtime')))
    store = Store(runtime/'ledgerwatch.db')
    registry = Registry(runtime/'models')

    @asynccontextmanager
    async def lifespan(app):
        if not (registry.directory/'current.txt').exists():
            train(registry.directory)
        registry.load()
        if seed_demo and store.transactions(limit=1)['total']==0:
            df = generate(120,seed=7)
            predictions = registry.score(df)
            store.save_batch([(row.transaction_id,{f:row[f] for f in FEATURES},pred)
                              for (_,row),pred in zip(df.iterrows(),predictions)])
        yield

    app = FastAPI(title='LedgerWatch',version='1.0.0',lifespan=lifespan,description='Synthetic anomaly scoring, review, and ML monitoring.')
    app.state.store,app.state.registry = store,registry
    app.state.metrics = {'requests':0,'errors':0,'seconds':0.0,'scored':0}

    def auth(credentials: HTTPAuthorizationCredentials=Depends(security)):
        if not secrets.compare_digest(credentials.credentials,os.getenv('API_TOKEN','demo-ledger-token')):
            raise HTTPException(401,'Invalid API token')

    @app.middleware('http')
    async def monitor(request,call_next):
        start = time.perf_counter()
        r = await call_next(request)
        if request.url.path not in ('/health','/metrics'):
            app.state.metrics['requests']+=1
            app.state.metrics['errors']+=int(r.status_code>=400)
            app.state.metrics['seconds']+=time.perf_counter()-start
        return r

    @app.get('/health')
    def health():
        try:
            meta = registry.load()
            return {'status':'ok','model_version':meta['version']}
        except (OSError,ValueError):
            raise HTTPException(503,'Model unavailable')

    @app.get('/metrics',response_class=PlainTextResponse)
    def metrics():
        m = app.state.metrics
        return f"ledgerwatch_requests_total {m['requests']}\nledgerwatch_errors_total {m['errors']}\nledgerwatch_scored_total {m['scored']}\nledgerwatch_request_seconds_sum {m['seconds']}\n"

    @app.get('/model',dependencies=[Depends(auth)])
    def model():
        meta = registry.load()
        return {k:v for k,v in meta.items() if k!='baselines'}

    def score_items(items):
        ids = [t.transaction_id for t in items]
        if len(ids)!=len(set(ids)):
            raise HTTPException(409,'Duplicate transaction IDs inside batch')
        frame = pd.DataFrame([{f:getattr(t,f) for f in FEATURES} for t in items])
        predictions = registry.score(frame)
        try:
            store.save_batch([(t.transaction_id,{f:getattr(t,f) for f in FEATURES},pred) for t,pred in zip(items,predictions)])
        except sqlite3.IntegrityError:
            raise HTTPException(409,'A transaction ID already exists. Entire request rolled back.')
        app.state.metrics['scored']+=len(items)
        return [{'transaction_id':t.transaction_id,**pred} for t,pred in zip(items,predictions)]

    @app.post('/score',dependencies=[Depends(auth)])
    def score(body:Transaction):
        return score_items([body])[0]

    @app.post('/batch',dependencies=[Depends(auth)])
    async def batch(file:UploadFile=File(...)):
        data = await file.read(1_000_001)
        if len(data)>1_000_000:
            raise HTTPException(413,'CSV exceeds 1 MB limit')
        try:
            frame = pd.read_csv(io.BytesIO(data),dtype={'transaction_id':str})
            if len(frame)<1 or len(frame)>1000:
                raise ValueError('CSV must contain 1 to 1000 rows')
            if set(frame.columns)!={'transaction_id',*FEATURES}:
                raise ValueError('CSV columns must be transaction_id and the six model features')
            items = [Transaction.model_validate(row) for row in frame.to_dict(orient='records')]
        except (ValidationError,ValueError,pd.errors.ParserError,UnicodeDecodeError) as exc:
            raise HTTPException(422,str(exc)[:500])
        return {'count':len(items),'predictions':score_items(items)}

    @app.get('/transactions',dependencies=[Depends(auth)])
    def transactions(flagged:bool|None=None,status:Literal['new','investigating','cleared','confirmed']|None=None,
                     limit:int=Query(100,ge=1,le=200),offset:int=Query(0,ge=0)):
        return store.transactions(flagged,status,limit,offset)

    @app.patch('/transactions/{id_}/review',dependencies=[Depends(auth)])
    def review(id_:str,body:Review):
        try:
            return store.review(id_,body.status,body.reason,body.expected_version)
        except KeyError:
            raise HTTPException(404,'Transaction not found')
        except ValueError as exc:
            raise HTTPException(409,str(exc))

    @app.get('/monitoring',dependencies=[Depends(auth)])
    def monitoring():
        meta = registry.load()
        stats = store.stats(meta['version'])
        rows = stats.pop('recent')
        drift = {}
        if len(rows)>=30:
            df = pd.DataFrame(rows)
            drift = {f:round(psi(df[f].to_numpy(),meta['baselines'][f]),4) for f in FEATURES}
        return {**stats,'model_version':meta['version'],'sample_size':len(rows),'drift':drift,
                'drift_alert':any(v>.2 for v in drift.values()),'drift_threshold':.2,
                'note':'PSI is a feature distribution heuristic; it does not measure model accuracy. At least 30 rows from the current model version are required.'}
    return app

app = create_app()
