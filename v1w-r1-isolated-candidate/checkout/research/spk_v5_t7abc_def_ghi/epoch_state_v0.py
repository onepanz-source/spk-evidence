"""T7DEF: serial, versioned, durable host-owned RESEARCH C-state between BV epochs.

No frozen P memory contract adoption. This SQLite ledger is not a trusted
source of identity; privileged host can rewrite state and recompute hashes.
"""
from __future__ import annotations
from pathlib import Path
import json,sqlite3
from research.spk_v5_t6abc_def_ghi.loop_v0 import digest
from .scheduler_bridge_v0 import BridgeRejected,check,CHOICES,GOALS

INITIAL={0:12,1:11}
GENESIS='0'*64
SCHEMA='spk-t7-research-bv-epoch-owned-state/v0'

class EpochState:
    def __init__(self,path,*,learn=True,create=True,budget=12):
        check(type(learn) is bool and type(budget) is int and 0<=budget<=48,'CONFIG_DOMAIN')
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(str(self.path),isolation_level=None,timeout=10)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('PRAGMA foreign_keys=ON')
        if create:
            check(self.db.execute("SELECT name FROM sqlite_master WHERE name='meta'").fetchone() is None,'DB_ALREADY_INITIALIZED')
            self.db.executescript('''
                CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE policy(cue INTEGER PRIMARY KEY,choice INTEGER NOT NULL,
                    version INTEGER NOT NULL,budget INTEGER NOT NULL);
                CREATE TABLE episode(id INTEGER PRIMARY KEY,cue INTEGER NOT NULL,choice INTEGER NOT NULL,
                    version INTEGER NOT NULL,goal INTEGER NOT NULL,status TEXT NOT NULL,
                    evidence_sha TEXT,outcome TEXT);
                CREATE TABLE ledger(seq INTEGER PRIMARY KEY,kind TEXT NOT NULL,body TEXT NOT NULL,
                    previous TEXT NOT NULL,hash TEXT NOT NULL);
            ''')
            self.db.execute('BEGIN IMMEDIATE')
            try:
                for k,v in {'schema':SCHEMA,'owner':'C','domain':'P','pe_id':'PE-C-RESEARCH',
                    'learn':str(int(learn)),'budget':str(budget)}.items():
                    self.db.execute('INSERT INTO meta VALUES(?,?)',(k,v))
                for cue,choice in sorted(INITIAL.items()):
                    self.db.execute('INSERT INTO policy VALUES(?,?,0,?)',(cue,choice,budget))
                self._append('INIT',{'learn':learn,'budget':budget,'initial':INITIAL})
                self.db.execute('COMMIT')
            except BaseException:
                self.db.execute('ROLLBACK');raise
        else:
            meta=dict(self.db.execute('SELECT key,value FROM meta'))
            check(meta=={'schema':SCHEMA,'owner':'C','domain':'P','pe_id':'PE-C-RESEARCH',
                        'learn':str(int(learn)),'budget':str(budget)},'REOPEN_CONFIG_DRIFT')
            self.audit()
        self.learn=learn
        self.initial_budget=budget

    def close(self):self.db.close()
    def reopen(self):
        learn=self.learn;budget=self.initial_budget
        self.close()
        self.__init__(self.path,create=False,learn=learn,budget=budget)

    def _append(self,kind,body):
        check(self.db.in_transaction,'UNSAFE_LEDGER_WRITE')
        prev=self.db.execute('SELECT seq,hash FROM ledger ORDER BY seq DESC LIMIT 1').fetchone()
        seq=prev['seq']+1 if prev is not None else 0
        old=prev['hash'] if prev is not None else GENESIS
        h=digest({'seq':seq,'kind':kind,'body':body,'previous':old})
        self.db.execute('INSERT INTO ledger VALUES(?,?,?,?,?)',
                        (seq,kind,json.dumps(body,sort_keys=True,separators=(',',':')),old,h))
        return h

    @property
    def table(self):return {r['cue']:r['choice'] for r in self.db.execute('SELECT * FROM policy')}
    @property
    def versions(self):return {r['cue']:r['version'] for r in self.db.execute('SELECT * FROM policy')}
    @property
    def updates(self):return sum(json.loads(r['body'])['updated'] for r in self.db.execute("SELECT body FROM ledger WHERE kind='SETTLE'"))

    def issue(self,cue,goal):
        check(type(cue) is int and cue in INITIAL,'BAD_CUE')
        check(type(goal) is int and goal in GOALS,'BAD_GOAL')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            check(self.db.execute("SELECT COUNT(*) FROM episode WHERE status='OPEN'").fetchone()[0]==0,'PENDING_CUSTODY')
            row=self.db.execute('SELECT * FROM policy WHERE cue=?',(cue,)).fetchone()
            ident=self.db.execute('SELECT COUNT(*) FROM episode').fetchone()[0]
            body={'id':ident,'cue':cue,'choice':row['choice'],'version':row['version'],'goal':goal}
            self.db.execute("INSERT INTO episode(id,cue,choice,version,goal,status) VALUES(?,?,?,?,?,'OPEN')",
                            (ident,cue,row['choice'],row['version'],goal))
            self._append('ISSUE',body)
            self.db.execute('COMMIT');return body
        except BaseException:
            self.db.execute('ROLLBACK');raise

    def unsettled(self):
        return [dict(x) for x in self.db.execute("SELECT id,cue,choice,version,goal FROM episode WHERE status='OPEN'")]

    def settle(self,issued,evidence):
        check(type(issued) is dict and set(issued)=={'id','cue','choice','version','goal'},'ISSUED_SCHEMA')
        check(type(evidence) is dict and set(evidence)=={'C_choice','A_outcome','A_emission','C_B_A',
            'reverse_A_B_C','full_BV_scheduler','eligible_to_update','source_sha256','source_batches',
            'source_bv_deliveries'},'EVIDENCE_SCHEMA')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            r=self.db.execute('SELECT * FROM episode WHERE id=?',(issued['id'],)).fetchone()
            check(r is not None and r['status']=='OPEN' and all(r[k]==issued[k] for k in issued),'STALE_OR_FORGED_ISSUE')
            state=self.db.execute('SELECT * FROM policy WHERE cue=?',(r['cue'],)).fetchone()
            check(state['version']==r['version'] and state['choice']==r['choice'],'POLICY_VERSION_DRIFT')
            check(evidence['C_choice']==r['choice'] and evidence['full_BV_scheduler'] is True,'SOURCE_CHOICE_DRIFT')
            check(type(evidence['source_sha256']) is str and len(evidence['source_sha256'])==64 and
                  all(ch in '0123456789abcdef' for ch in evidence['source_sha256']),'BAD_SOURCE_HASH')
            outcome=evidence['A_outcome'];check(outcome in ('IMPROVED','WORSENED','ABSENT'),'BAD_OUTCOME')
            present=outcome!='ABSENT'
            check(evidence['C_B_A'] is present and evidence['reverse_A_B_C'] is present and
                evidence['eligible_to_update'] is present and
                evidence['source_bv_deliveries']==(2 if present else 0),'INCONSISTENT_EVIDENCE')
            check(evidence['A_emission']==(21 if outcome=='IMPROVED' else 22 if outcome=='WORSENED' else None),
                  'A_VERDICT_CHANNEL_DRIFT')
            check(outcome=='ABSENT' or ((outcome=='IMPROVED')==(r['choice']==r['goal'])),'A_GOAL_COMPARISON_DRIFT')
            update=bool(self.learn and outcome=='WORSENED' and state['budget']>0 and present)
            if update:
                new=11 if r['choice']==12 else 12
                self.db.execute('UPDATE policy SET choice=?,version=version+1,budget=budget-1 WHERE cue=? AND version=?',
                                (new,r['cue'],r['version']))
            body={**issued,'source_sha256':evidence['source_sha256'],'outcome':outcome,'updated':update,
                  'new_choice':self.db.execute('SELECT choice FROM policy WHERE cue=?',(r['cue'],)).fetchone()[0]}
            self.db.execute("UPDATE episode SET status='SETTLED',evidence_sha=?,outcome=? WHERE id=?",
                            (evidence['source_sha256'],outcome,issued['id']))
            self._append('SETTLE',body)
            self.db.execute('COMMIT');return body
        except BaseException:
            self.db.execute('ROLLBACK');raise

    def audit(self):
        logs=list(self.db.execute('SELECT * FROM ledger ORDER BY seq'))
        check(logs,'EMPTY_LEDGER')
        expected={c:[v,0,int(dict(self.db.execute('SELECT key,value FROM meta'))['budget'])] for c,v in INITIAL.items()}
        prev=GENESIS;issued={};settled={}
        for i,row in enumerate(logs):
            check(row['seq']==i and row['previous']==prev,'LEDGER_SEQUENCE_DRIFT')
            try:body=json.loads(row['body'])
            except (ValueError,TypeError):raise BridgeRejected('INVALID_LEDGER_JSON')
            check(row['hash']==digest({'seq':i,'kind':row['kind'],'body':body,'previous':prev}), 'LEDGER_HASH_DRIFT')
            prev=row['hash']
            if row['kind']=='INIT':
                check(i==0 and body=={'learn':dict(self.db.execute('SELECT key,value FROM meta'))['learn']=='1',
                    'budget':expected[0][2],'initial':{'0':INITIAL[0],'1':INITIAL[1]}},'LEDGER_INIT')
            elif row['kind']=='ISSUE':
                c=body['cue'];eid=body['id']
                check(eid==len(issued) and eid not in settled and c in INITIAL and
                      body['choice']==expected[c][0] and body['version']==expected[c][1] and
                      body['goal'] in GOALS,'LEDGER_ISSUE')
                check(not any(j not in settled for j in issued),'CONCURRENT_EPOCH_FORBIDDEN')
                issued[eid]=body
            elif row['kind']=='SETTLE':
                eid=body['id'];check(eid in issued and eid not in settled,'LEDGER_SETTLE_ORDER')
                base=issued[eid];c=base['cue']
                check(all(body[k]==v for k,v in base.items()),'LEDGER_SETTLE_BINDING')
                check(body['outcome'] in ('IMPROVED','WORSENED','ABSENT'),'LEDGER_OUTCOME')
                check((body['outcome']=='IMPROVED')==(base['choice']==base['goal']) if body['outcome']!='ABSENT' else True,
                      'LEDGER_A_OUTCOME_DRIFT')
                can_update=body['outcome']=='WORSENED' and dict(self.db.execute('SELECT key,value FROM meta'))['learn']=='1' and expected[c][2]>0
                check(body['updated'] is can_update,'LEDGER_UPDATE_DRIFT')
                if can_update:
                    expected[c][0]=11 if expected[c][0]==12 else 12
                    expected[c][1]+=1;expected[c][2]-=1
                check(body['new_choice']==expected[c][0] and len(body['source_sha256'])==64,'LEDGER_RESULT_DRIFT')
                settled[eid]=body
            else:raise BridgeRejected('UNSUPPORTED_LEDGER_EVENT')
        material={r['cue']:[r['choice'],r['version'],r['budget']] for r in self.db.execute('SELECT * FROM policy')}
        check(material==expected,'MATERIALIZED_P_STATE_DRIFT')
        rows=list(self.db.execute('SELECT * FROM episode ORDER BY id'))
        check(len(rows)==len(issued),'EPISODE_COUNT_DRIFT')
        for r in rows:
            issued_row=issued[r['id']]
            check(all(r[k]==issued_row[k] for k in issued_row),'MATERIALIZED_ISSUE_DRIFT')
            check(r['status']==('SETTLED' if r['id'] in settled else 'OPEN'),'EPISODE_STATUS_DRIFT')
            if r['id'] in settled:
                x=settled[r['id']]
                check(r['evidence_sha']==x['source_sha256'] and r['outcome']==x['outcome'],'MATERIALIZED_OUTCOME_DRIFT')
            else:check(r['evidence_sha'] is None and r['outcome'] is None,'PENDING_EVIDENCE_DRIFT')
        return {'ledger_events':len(logs),'ledger_tip':prev,'episodes':len(rows),
            'settled':len(settled),'pending':len(issued)-len(settled),
            'updates':sum(b['updated'] for b in settled.values()),'policy':self.table,
            'versions':self.versions}
