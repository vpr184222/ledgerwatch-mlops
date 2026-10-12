from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.model import train,Registry,promote,psi
from app.data import generate,FEATURES

AUTH = {'Authorization':'Bearer demo-ledger-token'}
ROW = {'transaction_id':'TEST-1','amount':900,'hour':2,'account_age_days':8,'transactions_24h':16,'foreign':1,'distance_km':300}

@pytest.fixture(scope='module')
def runtime(tmp_path_factory):
    root = tmp_path_factory.mktemp('ledger')
    train(root/'models')
    return root

@pytest.fixture
def client(runtime,tmp_path):
    import shutil
    shutil.copytree(runtime/'models',tmp_path/'models')
    with TestClient(create_app(tmp_path,seed_demo=False)) as c:
        yield c

def test_training_split_metrics_and_baseline(runtime):
    registry = Registry(runtime/'models')
    meta = registry.load()
    assert (meta['train_rows'],meta['validation_rows'],meta['test_rows'])==(3000,1000,1000)
    assert 0<meta['threshold']<1
    assert meta['metrics']['average_precision']>meta['baseline_average_precision']
    scores = registry.score(generate(5,9))
    assert all(0<=r['score']<=1 for r in scores)

def test_drift_detects_shift(runtime):
    meta = Registry(runtime/'models').load()
    stable,shifted = generate(1000,3),generate(1000,3,True)
    baseline = meta['baselines']['amount']
    assert psi(shifted.amount.to_numpy(),baseline)>.2
    assert psi(stable.amount.to_numpy(),baseline)<.1

def test_score_review_and_auth(client):
    assert client.post('/score',json=ROW).status_code in (401,403)
    r = client.post('/score',headers=AUTH,json=ROW)
    assert r.status_code==200 and 0<=r.json()['score']<=1
    assert client.post('/score',headers=AUTH,json=ROW).status_code==409
    invalid = {**ROW,'transaction_id':'BAD','amount':-1}
    assert client.post('/score',headers=AUTH,json=invalid).status_code==422
    invalid = {**ROW,'transaction_id':'BAD','hour':25}
    assert client.post('/score',headers=AUTH,json=invalid).status_code==422
    review = {'status':'investigating','reason':'Suspicious synthetic pattern','expected_version':0}
    assert client.patch('/transactions/TEST-1/review',headers=AUTH,json=review).status_code==200
    assert client.patch('/transactions/TEST-1/review',headers=AUTH,json=review).status_code==409
    assert client.get('/monitoring',headers=AUTH).json()['reviewed']==1

def test_batch_atomicity_and_invalid_csv(client):
    client.post('/score',headers=AUTH,json=ROW)
    df = pd.DataFrame([{**ROW,'transaction_id':'TEST-2'},ROW])
    r = client.post('/batch',headers=AUTH,files={'file':('data.csv',df.to_csv(index=False),'text/csv')})
    assert r.status_code==409
    assert client.get('/transactions',headers=AUTH).json()['total']==1
    df = pd.DataFrame([{**ROW,'transaction_id':'A'},{**ROW,'transaction_id':'A'}])
    assert client.post('/batch',headers=AUTH,files={'file':('data.csv',df.to_csv(index=False))}).status_code==409
    assert client.post('/batch',headers=AUTH,files={'file':('bad.csv','hello,world\n1,2')}).status_code==422
    assert client.post('/batch',headers=AUTH,files={'file':('large.csv',b'x'*1_000_001)}).status_code==413

def test_monitoring_filtered_to_active_version(client):
    df = generate(40,77,True)[['transaction_id',*FEATURES]]
    r = client.post('/batch',headers=AUTH,files={'file':('drift.csv',df.to_csv(index=False))})
    assert r.status_code==200
    m = client.get('/monitoring',headers=AUTH).json()
    assert m['sample_size']==40 and m['drift_alert']
    page = client.get('/transactions?limit=10&offset=10',headers=AUTH).json()
    assert page['total']==40 and len(page['items'])==10

def test_promotion_and_rollback(runtime,tmp_path):
    import shutil
    shutil.copytree(runtime/'models',tmp_path/'models')
    registry = Registry(tmp_path/'models')
    first = registry.load()['version']
    second = train(tmp_path/'models',seed=17,activate=False)['version']
    assert registry.load()['version']==first
    promote(tmp_path/'models',second)
    assert registry.load()['version']==second
    promote(tmp_path/'models',first)
    assert registry.load()['version']==first
    with pytest.raises(ValueError):
        promote(tmp_path/'models','../outside')
