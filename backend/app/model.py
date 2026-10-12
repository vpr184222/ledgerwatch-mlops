import json
import os
from threading import RLock
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, roc_auc_score, precision_recall_curve, precision_score, recall_score, f1_score
from .data import generate, FEATURES

def metrics(y, scores, threshold):
    pred = scores>=threshold
    return {'average_precision':float(average_precision_score(y,scores)),
            'roc_auc':float(roc_auc_score(y,scores)),
            'precision':float(precision_score(y,pred,zero_division=0)),
            'recall':float(recall_score(y,pred,zero_division=0)),
            'f1':float(f1_score(y,pred,zero_division=0)),
            'positive_rate':float(np.mean(y))}

def train(directory, seed=42, track=False, activate=True):
    directory = Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    df = generate(5000,seed)
    train_df, val, test = df.iloc[:3000],df.iloc[3000:4000],df.iloc[4000:]
    model = RandomForestClassifier(n_estimators=100,max_depth=8,min_samples_leaf=10,class_weight='balanced',random_state=seed,n_jobs=1)
    model.fit(train_df[FEATURES],train_df.label)
    val_scores = model.predict_proba(val[FEATURES])[:,1]
    precision, recall, thresholds = precision_recall_curve(val.label,val_scores)
    f1 = 2*precision[:-1]*recall[:-1]/np.maximum(precision[:-1]+recall[:-1],1e-10)
    threshold = float(thresholds[int(np.argmax(f1))])
    version = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid4().hex[:8]
    folder = directory/version
    folder.mkdir()
    test_scores = model.predict_proba(test[FEATURES])[:,1]
    baselines = {}
    for feature in FEATURES:
        values = train_df[feature].to_numpy()
        if feature=='foreign':
            edges = np.array([-np.inf,.5,np.inf])
        else:
            internal = np.unique(np.quantile(values,np.linspace(.1,.9,9)))
            edges = np.concatenate(([-np.inf],internal,[np.inf]))
        counts = np.histogram(values,bins=edges)[0]
        # JSON finite sentinels represent open-ended bins.
        baselines[feature] = {'edges':[None if not np.isfinite(x) else float(x) for x in edges],
                              'proportions':(counts/counts.sum()).tolist()}
    meta = {'version':version,'seed':seed,'created_at':datetime.now(timezone.utc).isoformat(),
            'threshold':threshold,'features':FEATURES,'train_rows':3000,'validation_rows':1000,'test_rows':1000,
            'split':'chronological 60/20/20; threshold selected on validation F1 only',
            'metrics':metrics(test.label,test_scores,threshold),
            'baseline_average_precision':float(test.label.mean()),
            'feature_importance':dict(zip(FEATURES,map(float,model.feature_importances_))), 'baselines':baselines}
    joblib.dump(model,folder/'model.joblib')
    (folder/'metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    if track:
        import mlflow
        mlflow.set_tracking_uri(os.getenv('MLFLOW_TRACKING_URI',(directory.parent/'mlruns').resolve().as_uri()))
        mlflow.set_experiment('ledgerwatch-synthetic')
        with mlflow.start_run(run_name=version) as run:
            mlflow.log_params({'seed':seed,'n_estimators':100,'max_depth':8,'train_rows':3000,'threshold':threshold})
            mlflow.log_metrics(meta['metrics'])
            mlflow.log_artifacts(str(folder),artifact_path='model_bundle')
            meta['mlflow_run_id'] = run.info.run_id
        (folder/'metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    if activate:
        promote(directory,version)
    return meta

def promote(directory, version):
    directory = Path(directory)
    if not version or Path(version).name!=version or version in ('.','..'):
        raise ValueError('Invalid model version')
    folder = directory/version
    if not (folder/'model.joblib').is_file() or not (folder/'metadata.json').is_file():
        raise ValueError('Model version does not contain a complete bundle')
    # A unique temporary file avoids collisions between concurrent promotion commands.
    temp = directory/('current-'+uuid4().hex+'.tmp')
    temp.write_text(version,encoding='utf-8')
    os.replace(temp,directory/'current.txt')

class Registry:
    def __init__(self,directory):
        self.directory = Path(directory)
        self.model = None
        self.meta = None
        self.loaded = None
        self.lock = RLock()

    def load(self):
        with self.lock:
            return self._load()

    def _load(self):
        version = (self.directory/'current.txt').read_text(encoding='utf-8').strip()
        if self.loaded != version:
            # Only load locally generated/trusted artifacts. Joblib is not safe for untrusted models.
            model = joblib.load(self.directory/version/'model.joblib')
            meta = json.loads((self.directory/version/'metadata.json').read_text(encoding='utf-8'))
            self.model,self.meta,self.loaded = model,meta,version
        return self.meta

    def score(self, frame):
        with self.lock:
            meta = self._load()
            scores = self.model.predict_proba(frame[FEATURES])[:,1]
        return [{'score':round(float(s),6),'flagged':bool(s>=meta['threshold']),'model_version':meta['version'],
                 'threshold':meta['threshold']} for s in scores]

def psi(values, baseline):
    edges = np.array([(-np.inf if i==0 else np.inf) if x is None else x for i,x in enumerate(baseline['edges'])])
    counts = np.histogram(values,bins=edges)[0]
    observed = counts/max(counts.sum(),1)
    expected = np.array(baseline['proportions'])
    a,b = np.maximum(observed,1e-6),np.maximum(expected,1e-6)
    return float(np.sum((a-b)*np.log(a/b)))
