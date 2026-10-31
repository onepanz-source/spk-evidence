"""T8STU: research-owned, truly event-driven tick V1 runtime, not frozen BV.

Each C/B/A, A->B and B->C stage is a separately persisted scheduler event.
The PE kernel is the unchanged Architecture v1b _compute_local primitive.
The negative A verdict causes a versioned, atomic P grant/commit *inside this
new reference scheduler's B->C tick*, not in an after-the-fact adapter.
There is no attested source, no native SPK Memory Contract, and no native BV.
"""
from __future__ import annotations
import json, sqlite3
from pathlib import Path
from types import SimpleNamespace
from spk_architecture_v1.pe_execution_v1b import _compute_local
from research.spk_v5_t6abc_def_ghi.loop_v0 import digest

SCHEMA='spk-v1-reference-integrated-tick-semantic-P/v1'
INIT={0:12,1:11}
ZERO='0'*64

class Reject(ValueError): pass

def ensure(ok, code):
    if not ok:raise Reject(code)

def pack(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)

def pe_step(nid, choice, goal, tick, channels):
    """Invoke frozen local PE semantics rather than fabricate outcomes."""
    programs={
      'C':(('ACC',(1,1)),('CMP',1),('EMIT',choice),('RESET',0)),
      'B':(('ACC',(1,1)),('CMP',1),('EMIT',13),('RESET',0),('ACC',(1,2)),('CMP',1),('EMIT',14),('RESET',0)),
      'A':(('ACC',(1,3)),('CMP',1),('EMIT',21 if goal==11 else 22),('EMIT',7),('RESET',0),
           ('ACC',(1,4)),('CMP',1),('EMIT',21 if goal==12 else 22),('EMIT',7),('RESET',0))}
    ensure(nid in programs and choice in (11,12) and goal in (11,12),'PE_PROGRAM_DOMAIN')
    node=SimpleNamespace(instructions=programs[nid],state_bits=16,fractional_bits=0)
    raw,guard,emits=_compute_local(node,(0,0),tick,tuple(channels))
    return {'node':nid,'tick':tick,'channels':list(channels),'raw':raw,'guard':guard,'emits':list(emits)}

class TickEngine:
    def __init__(self,path,*,learn=True,budget=12,create=True):
        ensure(type(learn) is bool and type(budget) is int and 0<=budget<=48,'CONFIG')
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.learn=learn;self.budget=budget
        self.db=sqlite3.connect(str(self.path),isolation_level=None,timeout=20)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('PRAGMA foreign_keys=ON')
        if create:
            ensure(self.db.execute("SELECT 1 FROM sqlite_master WHERE name='meta'").fetchone() is None,'ALREADY_INITIALIZED')
            self.db.executescript('''
              CREATE TABLE meta(k TEXT PRIMARY KEY,v TEXT NOT NULL);
              CREATE TABLE p(cue INTEGER PRIMARY KEY,choice INTEGER NOT NULL,version INTEGER NOT NULL,budget INTEGER NOT NULL);
              CREATE TABLE episode(id INTEGER PRIMARY KEY,cue INTEGER NOT NULL,goal INTEGER NOT NULL,choice INTEGER NOT NULL,version INTEGER NOT NULL,drop_forward INTEGER NOT NULL,drop_feedback INTEGER NOT NULL,feedback_delay INTEGER NOT NULL,status TEXT NOT NULL,outcome TEXT,reference_grant INTEGER);
              CREATE TABLE event(id INTEGER PRIMARY KEY,episode_id INTEGER NOT NULL REFERENCES episode(id),tick INTEGER NOT NULL,kind TEXT NOT NULL,payload TEXT NOT NULL,digest TEXT NOT NULL,status TEXT NOT NULL);
              CREATE TABLE p_grant(id INTEGER PRIMARY KEY,episode_id INTEGER NOT NULL UNIQUE REFERENCES episode(id),cue INTEGER NOT NULL,expected_version INTEGER NOT NULL,verdict_digest TEXT NOT NULL,consumed INTEGER NOT NULL);
              CREATE TABLE ledger(seq INTEGER PRIMARY KEY,kind TEXT NOT NULL,payload TEXT NOT NULL,previous TEXT NOT NULL,digest TEXT NOT NULL);
            ''')
            self.db.execute('BEGIN IMMEDIATE')
            try:
                for k,v in {'schema':SCHEMA,'owner':'C','domain':'P','mode':'execute','learn':str(int(learn)),'budget':str(budget)}.items():
                    self.db.execute('INSERT INTO meta VALUES(?,?)',(k,v))
                for cue,ch in sorted(INIT.items()):self.db.execute('INSERT INTO p VALUES(?,?,0,?)',(cue,ch,budget))
                self._log('INIT',{'initial':INIT,'learn':learn,'budget':budget})
                self.db.execute('COMMIT')
            except BaseException:self.db.execute('ROLLBACK');raise
        else:
            expect={'schema':SCHEMA,'owner':'C','domain':'P','mode':'execute','learn':str(int(learn)),'budget':str(budget)}
            ensure(dict(self.db.execute('SELECT k,v FROM meta'))==expect,'META_DRIFT')
            self.audit()

    def close(self):self.db.close()
    def reopen(self):
        self.close();self.__init__(self.path,learn=self.learn,budget=self.budget,create=False)

    def _log(self,kind,payload):
        ensure(self.db.in_transaction,'NONATOMIC_LOG')
        previous=self.db.execute('SELECT seq,digest FROM ledger ORDER BY seq DESC LIMIT 1').fetchone()
        n=previous['seq']+1 if previous else 0
        prev=previous['digest'] if previous else ZERO
        hash_=digest({'seq':n,'kind':kind,'payload':payload,'prev':prev})
        self.db.execute('INSERT INTO ledger VALUES(?,?,?,?,?)',(n,kind,pack(payload),prev,hash_))

    def _enqueue(self,ep,tick,kind,payload):
        ensure(self.db.in_transaction and type(tick) is int and tick>=10,'EVENT_CLOCK')
        eid=self.db.execute('SELECT COUNT(*) FROM event').fetchone()[0]
        h=digest({'id':eid,'episode':ep,'tick':tick,'kind':kind,'payload':payload})
        self.db.execute('INSERT INTO event VALUES(?,?,?,?,?,?,?)',(eid,ep,tick,kind,pack(payload),h,'QUEUED'))
        self._log('QUEUE',{'event_id':eid,'episode':ep,'kind':kind,'tick':tick,'hash':h})
        return eid

    def submit(self,cue,goal,*,drop_forward=False,drop_feedback=False,feedback_delay=0):
        ensure(type(cue) is int and cue in INIT and type(goal) is int and goal in (11,12),'TASK_DOMAIN')
        ensure(type(drop_forward) is bool and type(drop_feedback) is bool and type(feedback_delay) is int and 0<=feedback_delay<=12,'TASK_FLAGS')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            ensure(self.db.execute("SELECT count(*) FROM episode WHERE status='RUNNING'").fetchone()[0]==0,'ONE_EPOCH_AT_A_TIME')
            p=self.db.execute('SELECT * FROM p WHERE cue=?',(cue,)).fetchone()
            ep=self.db.execute('SELECT COUNT(*) FROM episode').fetchone()[0]
            self.db.execute("INSERT INTO episode VALUES(?,?,?,?,?,?,?,?, 'RUNNING',NULL,NULL)",
                (ep,cue,goal,p['choice'],p['version'],int(drop_forward),int(drop_feedback),feedback_delay))
            self._log('ISSUE',{'id':ep,'cue':cue,'goal':goal,'choice':p['choice'],'version':p['version'],
                'drop_forward':drop_forward,'drop_feedback':drop_feedback,'feedback_delay':feedback_delay})
            self._enqueue(ep,10,'PE_C',{'input':[1]})
            self.db.execute('COMMIT')
            return ep
        except BaseException:self.db.execute('ROLLBACK');raise

    def _ev(self,eid):
        row=self.db.execute('SELECT * FROM event WHERE id=?',(eid,)).fetchone()
        ensure(row is not None and row['status']=='DONE','MISSING_PARENT_EVENT')
        data=json.loads(row['payload'])
        ensure(row['digest']==digest({'id':row['id'],'episode':row['episode_id'],'tick':row['tick'],'kind':row['kind'],'payload':data}),'PARENT_DIGEST_DRIFT')
        return row,data

    def _settle(self,ep, outcome,grant_id=None):
        self.db.execute('UPDATE episode SET status=?,outcome=?,reference_grant=? WHERE id=? AND status=?',
            ('SETTLED',outcome,grant_id,ep,'RUNNING'))
        ensure(self.db.execute('SELECT changes()').fetchone()[0]==1,'DUPLICATE_SETTLE')
        self._log('SETTLE',{'episode':ep,'outcome':outcome,'grant':grant_id})

    def step(self):
        """Atomically execute exactly one real tick event. Safe at each process boundary."""
        self.db.execute('BEGIN IMMEDIATE')
        try:
            r=self.db.execute("SELECT * FROM event WHERE status='QUEUED' ORDER BY tick,id LIMIT 1").fetchone()
            if r is None:
                self.db.execute('COMMIT');return None
            body=json.loads(r['payload'])
            ensure(r['digest']==digest({'id':r['id'],'episode':r['episode_id'],'tick':r['tick'],'kind':r['kind'],'payload':body}),'EVENT_DIGEST_DRIFT')
            ep=self.db.execute('SELECT * FROM episode WHERE id=?',(r['episode_id'],)).fetchone()
            ensure(ep is not None and ep['status']=='RUNNING','EVENT_EPISODE_STALE')
            i,kind,t=r['id'],r['kind'],r['tick']
            self.db.execute("UPDATE event SET status='DONE' WHERE id=? AND status='QUEUED'",(i,))
            ensure(self.db.execute('SELECT changes()').fetchone()[0]==1,'EVENT_REPLAY')
            outcome=None
            if kind=='PE_C':
                ensure(t==10 and body=={'input':[1]},'C_EVENT_INVALID')
                x=pe_step('C',ep['choice'],ep['goal'],t,[1]);ensure(x['emits']==[ep['choice']],'C_OUTPUT_DRIFT')
                if ep['drop_forward']:
                    self._enqueue(ep['id'],11,'QUIESCE',{'parent':i,'why':'FORWARD_LOST'})
                else:
                    self._enqueue(ep['id'],11,'PE_B',{'parent':i,'channel':ep['choice'],'pe':x})
            elif kind=='PE_B':
                ensure(t==11,'B_CLOCK');p,prev=self._ev(body['parent'])
                ensure(p['kind']=='PE_C' and body['pe']['emits']==[ep['choice']] and
                    body['channel']==ep['choice'],'B_LINEAGE')
                ch=1 if ep['choice']==11 else 2
                x=pe_step('B',ep['choice'],ep['goal'],t,[ch]);expected=13 if ch==1 else 14
                ensure(x['emits']==[expected],'B_OUTPUT_DRIFT')
                self._enqueue(ep['id'],12,'PE_A',{'parent':i,'channel':expected,'pe':x})
            elif kind=='PE_A':
                ensure(t==12,'A_CLOCK');p,_=self._ev(body['parent']);ensure(p['kind']=='PE_B','A_LINEAGE')
                x=pe_step('A',ep['choice'],ep['goal'],t,[3 if body['channel']==13 else 4])
                wanted=21 if ep['choice']==ep['goal'] else 22
                ensure(x['emits']==[wanted,7],'A_SEMANTIC_DRIFT')
                outcome='IMPROVED' if wanted==21 else 'WORSENED'
                capsule={'issuer':'A','receiver':'C','decision':ep['id'],'cue':ep['cue'],
                    'choice':ep['choice'],'version':ep['version'],'verdict':outcome,
                    'A_PE_digest':digest(x),'A_event':i,'A_event_digest':r['digest'],
                    'C_source':'REFERENCE_SIMULATED_PE','authentication':'UNATTESTED'}
                if ep['drop_feedback']:
                    self._enqueue(ep['id'],13,'QUIESCE',{'parent':i,'why':'FEEDBACK_LOST','outcome':outcome})
                else:
                    self._enqueue(ep['id'],13+ep['feedback_delay'],'SEM_A_B',{'parent':i,'capsule':capsule})
            elif kind=='SEM_A_B':
                p,pbody=self._ev(body['parent']);ensure(p['kind']=='PE_A' and t==13+ep['feedback_delay'],'FEEDBACK_A_B_LINEAGE')
                cap=body['capsule'];ensure(cap['A_event']==p['id'] and cap['A_event_digest']==p['digest'] and
                     cap['decision']==ep['id'] and cap['choice']==ep['choice'] and cap['version']==ep['version'] and
                     cap['cue']==ep['cue'] and cap['issuer']=='A' and cap['receiver']=='C' and
                     cap['A_PE_digest']==digest(pe_step('A',ep['choice'],ep['goal'],12,[3 if ep['choice']==11 else 4])) and
                     cap['verdict']==('IMPROVED' if ep['choice']==ep['goal'] else 'WORSENED') and
                     cap['authentication']=='UNATTESTED','SEMANTIC_A_BINDING')
                self._enqueue(ep['id'],t+1,'SEM_B_C',{'parent':i,'capsule':cap,'relay_digest':r['digest']})
            elif kind=='SEM_B_C':
                p,pbody=self._ev(body['parent']);ensure(p['kind']=='SEM_A_B' and t==p['tick']+1,'FEEDBACK_B_C_LINEAGE')
                cap=body['capsule'];ensure(cap==pbody['capsule'] and body['relay_digest']==p['digest'] and
                    cap['decision']==ep['id'],'FEEDBACK_B_C_BINDING')
                outcome=cap['verdict']
                state=self.db.execute('SELECT * FROM p WHERE cue=?',(ep['cue'],)).fetchone()
                ensure(state['choice']==ep['choice'] and state['version']==ep['version'],'STALE_POLICY_VERSION')
                grant=None
                # Deadline is the 18th tick: delayed feedback may arrive but is not admissible.
                if t<=18 and outcome=='WORSENED' and self.learn and state['budget']>0:
                    grant=self.db.execute('SELECT COUNT(*) FROM p_grant').fetchone()[0]
                    self.db.execute('INSERT INTO p_grant VALUES(?,?,?,?,?,1)',(grant,ep['id'],ep['cue'],ep['version'],digest(cap)))
                    self._log('GRANT_P',{'grant':grant,'episode':ep['id'],'owner':'C','domain':'P',
                        'mode':'execute','expected_version':ep['version'],'receipt_digest':digest(cap)})
                    self.db.execute('UPDATE p SET choice=?,version=version+1,budget=budget-1 WHERE cue=? AND version=?',
                        (11 if state['choice']==12 else 12,ep['cue'],ep['version']))
                    ensure(self.db.execute('SELECT changes()').fetchone()[0]==1,'P_CAS_FAILED')
                self._settle(ep['id'],outcome,grant)
            elif kind=='QUIESCE':
                p,_=self._ev(body['parent'])
                ensure((body['why']=='FORWARD_LOST' and p['kind']=='PE_C') or
                    (body['why']=='FEEDBACK_LOST' and p['kind']=='PE_A'),'QUIESCE_PARENT')
                self._settle(ep['id'],body.get('outcome','ABSENT'))
            else:raise Reject('UNSUPPORTED_EVENT_KIND')
            self._log('EXECUTE',{'id':i,'tick':t,'kind':kind,'episode':ep['id']})
            self.db.execute('COMMIT')
            return {'tick':t,'event':i,'kind':kind,'episode':ep['id']}
        except BaseException:self.db.execute('ROLLBACK');raise

    def run(self,max_events=16):
        ensure(type(max_events) is int and 1<=max_events<=128,'STEP_BUDGET')
        steps=[]
        for _ in range(max_events):
            next_=self.step()
            if next_ is None:break
            steps.append(next_)
        ensure(self.db.execute("SELECT COUNT(*) FROM event WHERE status='QUEUED'").fetchone()[0]==0,'RUNTIME_NOT_QUIESCENT')
        return steps

    def result(self,ep):
        r=self.db.execute('SELECT * FROM episode WHERE id=?',(ep,)).fetchone()
        ensure(r is not None and r['status']=='SETTLED','RESULT_NOT_SETTLED')
        return {'id':r['id'],'cue':r['cue'],'goal':r['goal'],'choice':r['choice'],
            'version':r['version'],'outcome':r['outcome'],'grant':r['reference_grant'],
            'semantic_events':[x[0] for x in self.db.execute("SELECT kind FROM event WHERE episode_id=? AND kind LIKE 'SEM_%' ORDER BY id",(ep,))]}

    def audit(self):
        prev=ZERO
        logs=list(self.db.execute('SELECT * FROM ledger ORDER BY seq'))
        ensure(bool(logs),'EMPTY_LEDGER')
        for idx,r in enumerate(logs):
            ensure(r['seq']==idx and r['previous']==prev and
                r['digest']==digest({'seq':idx,'kind':r['kind'],'payload':json.loads(r['payload']),'prev':prev}),'LEDGER_CHAIN_DRIFT')
            prev=r['digest']
        for e in self.db.execute('SELECT * FROM event'):
            ensure(e['digest']==digest({'id':e['id'],'episode':e['episode_id'],'tick':e['tick'],
                'kind':e['kind'],'payload':json.loads(e['payload'])}),'EVENT_AUDIT_DRIFT')
        grants=list(self.db.execute('SELECT * FROM p_grant'))
        state=list(self.db.execute('SELECT * FROM p ORDER BY cue'))
        ensure(len(grants)==sum(r['version'] for r in state),'P_VERSION_GRANT_DRIFT')
        ensure(all(r['choice']==(INIT[r['cue']] if r['version']%2==0 else 11 if INIT[r['cue']]==12 else 12)
             and r['budget']==self.budget-r['version'] for r in state),'P_STATE_DRIFT')
        ensure(all(g['consumed']==1 for g in grants),'UNCONSUMED_GRANT')
        settled=list(self.db.execute("SELECT * FROM episode WHERE status='SETTLED'"))
        issued=self.db.execute('SELECT count(*) FROM episode').fetchone()[0]
        pending=self.db.execute("SELECT count(*) FROM event WHERE status='QUEUED'").fetchone()[0]
        ensure(issued==len(settled)+sum(1 for _ in self.db.execute("SELECT 1 FROM episode WHERE status='RUNNING'")),'ISSUE_STATUS_DRIFT')
        return {'episodes':issued,'settled':len(settled),'pending_events':pending,
            'reference_v1_tick_grants':len(grants),'P_writes':sum(r['version'] for r in state),
            'P_policy':{r['cue']:r['choice'] for r in state},
            'P_versions':{r['cue']:r['version'] for r in state},'ledger_events':len(logs),'ledger_tip':prev}
