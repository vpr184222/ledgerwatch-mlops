import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime,timezone
from uuid import uuid4

class Store:
    def __init__(self,path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS transactions(id TEXT PRIMARY KEY, features TEXT, score REAL,
              flagged INTEGER, model_version TEXT, status TEXT DEFAULT 'new', version INTEGER DEFAULT 0, created_at TEXT);
            CREATE TABLE IF NOT EXISTS audit(id TEXT PRIMARY KEY, transaction_id TEXT, status TEXT, reason TEXT, created_at TEXT);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path,timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def save_batch(self,rows):
        # Whole upload is atomic; duplicate IDs leave no partially written batch.
        with self.connect() as db:
            for id_,features,pred in rows:
                db.execute('INSERT INTO transactions(id,features,score,flagged,model_version,created_at) VALUES(?,?,?,?,?,?)',
                    (id_,json.dumps(features),pred['score'],int(pred['flagged']),pred['model_version'],datetime.now(timezone.utc).isoformat()))

    def transactions(self,flagged=None,status=None,limit=100,offset=0):
        clauses,args = [],[]
        if flagged is not None:
            clauses.append('flagged=?');args.append(int(flagged))
        if status:
            clauses.append('status=?');args.append(status)
        where = ' WHERE '+' AND '.join(clauses) if clauses else ''
        with self.connect() as db:
            total = db.execute('SELECT count(*) FROM transactions'+where,args).fetchone()[0]
            rows = db.execute('SELECT * FROM transactions'+where+' ORDER BY created_at DESC, id LIMIT ? OFFSET ?',args+[limit,offset])
            items = [{**dict(r),'features':json.loads(r['features']),'flagged':bool(r['flagged'])} for r in rows]
            return {'items':items,'total':total,'limit':limit,'offset':offset}

    def review(self,id_,status,reason,version):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT version FROM transactions WHERE id=?',(id_,)).fetchone()
            if row is None:
                raise KeyError(id_)
            if row['version'] != version:
                raise ValueError('Transaction changed. Refresh before reviewing again.')
            db.execute('UPDATE transactions SET status=?,version=version+1 WHERE id=?',(status,id_))
            db.execute('INSERT INTO audit VALUES(?,?,?,?,?)',(str(uuid4()),id_,status,reason,datetime.now(timezone.utc).isoformat()))
            return {'id':id_,'status':status,'version':version+1}

    def stats(self,model_version):
        with self.connect() as db:
            total,flagged = db.execute('SELECT count(*),coalesce(sum(flagged),0) FROM transactions').fetchone()
            reviewed = db.execute("SELECT count(*) FROM transactions WHERE status!='new'").fetchone()[0]
            rows = db.execute('SELECT features FROM transactions WHERE model_version=? ORDER BY created_at DESC LIMIT 1000',(model_version,)).fetchall()
            audit = [dict(r) for r in db.execute('SELECT * FROM audit ORDER BY created_at DESC LIMIT 10')]
            return {'total':total,'flagged':flagged,'reviewed':reviewed,'recent':[json.loads(r['features']) for r in rows],'audit':audit}
