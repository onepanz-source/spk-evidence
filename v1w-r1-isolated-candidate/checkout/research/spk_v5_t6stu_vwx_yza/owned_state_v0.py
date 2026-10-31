"""SPK T6STU/VWX/YZA: experimental C-owned persistent P-state port.

SQLite WAL transactions and a replay-checked event ledger, constrained to the
research PE fragment. Not frozen Memory Contract integration, not a trusted
hardware boundary, and not native BV/plasticity. A privileged host can edit DB,
forge messages, or re-author a consistent ledger.
"""
from __future__ import annotations
import copy
import json
import sqlite3
from pathlib import Path
from research.spk_v5_t6abc_def_ghi.loop_v0 import require, digest, emit_single, LoopBoundary
from research.spk_v5_t6jkl_mno_pqr.async_multi_v0 import RECEIVERS, FEEDBACK_CHANNEL

SCHEMA='spk-research-owned-c-state-sqlite/v0'
OWNER='C'
PE_ID='PE-C-RESEARCH'
INITIAL={0:12, 1:11}
GENESIS='0'*64

class OwnedCState:
    def __init__(self, path:Path|str, *, learn:bool=True, budget:int=8, create:bool=True):
        require(type(learn) is bool and type(budget) is int and 0<=budget<=32, 'POLICY_ARGS')
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(str(self.path),isolation_level=None,timeout=10.0)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA busy_timeout=10000')
        if create:
            require(not self.db.execute("SELECT name FROM sqlite_master WHERE name='meta'").fetchone(), 'REINITIALIZATION_FORBIDDEN')
            self.db.executescript('''
                CREATE TABLE meta(k TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE policy(cue INTEGER PRIMARY KEY CHECK(cue IN (0,1)),
                    choice INTEGER NOT NULL CHECK(choice IN (11,12)),
                    version INTEGER NOT NULL CHECK(version>=0),
                    budget INTEGER NOT NULL CHECK(budget>=0));
                CREATE TABLE decisions(id INTEGER PRIMARY KEY,cue INTEGER NOT NULL,
                    choice INTEGER NOT NULL, version INTEGER NOT NULL,issue_tick INTEGER NOT NULL,
                    decision_sha TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('OPEN','COMPLETE','CLOSED')));
                CREATE TABLE votes(decision_id INTEGER NOT NULL,receiver TEXT NOT NULL,
                    outcome TEXT NOT NULL, vote_sha TEXT NOT NULL,
                    PRIMARY KEY(decision_id,receiver));
                CREATE TABLE results(id INTEGER PRIMARY KEY,result TEXT NOT NULL,transcript TEXT NOT NULL);
                CREATE TABLE ledger(seq INTEGER PRIMARY KEY,kind TEXT NOT NULL,
                    body TEXT NOT NULL,prev TEXT NOT NULL,seal TEXT NOT NULL UNIQUE);
            ''')
            self.db.execute('BEGIN IMMEDIATE')
            try:
                for k,v in {'schema':SCHEMA,'owner':OWNER,'pe_id':PE_ID,
                            'domain':'P','mode':'execute','learn':str(int(learn)),'initial_budget':str(budget)}.items():
                    self.db.execute('INSERT INTO meta VALUES (?,?)',(k,v))
                for cue,choice in sorted(INITIAL.items()):
                    self.db.execute('INSERT INTO policy VALUES (?,?,?,?)',(cue,choice,0,budget))
                self._append('INIT',{'owner':OWNER,'pe':PE_ID,'learn':learn,'budget':budget})
                self.db.execute('COMMIT')
            except Exception:
                self.db.execute('ROLLBACK');raise
        else:
            require(self.meta('schema')==SCHEMA and self.meta('owner')==OWNER and
                    self.meta('pe_id')==PE_ID and self.meta('domain')=='P' and
                    self.meta('mode')=='execute','INVALID_STATE_OWNER_OR_SCHEMA')
            require(self.learn==learn and int(self.meta('initial_budget'))==budget,'STATE_CONFIG_DRIFT')
            self.audit()

    def meta(self,key):
        x=self.db.execute('SELECT value FROM meta WHERE k=?',(key,)).fetchone()
        require(x is not None, 'MISSING_META');return x[0]
    @property
    def learn(self): return self.meta('learn')=='1'
    @property
    def table(self):return {int(r['cue']):int(r['choice']) for r in self.db.execute('SELECT * FROM policy')}
    @property
    def versions(self):return {int(r['cue']):int(r['version']) for r in self.db.execute('SELECT * FROM policy')}
    @property
    def budget(self):return {int(r['cue']):int(r['budget']) for r in self.db.execute('SELECT * FROM policy')}
    @property
    def updates(self):return sum(r['result']=='UPDATED' for r in self.db.execute('SELECT result FROM results'))
    @property
    def judged(self):return self.db.execute('SELECT count(*) FROM results').fetchone()[0]
    @property
    def conflicts(self):return sum(r['result']=='CONFLICT_HELD' for r in self.db.execute('SELECT result FROM results'))
    @property
    def accepted_votes(self):return self.db.execute('SELECT count(*) FROM votes').fetchone()[0]
    @property
    def transcripts(self):return [json.loads(r['body']) for r in self.db.execute("SELECT body FROM ledger WHERE kind='SETTLE' ORDER BY seq")]

    def close(self): self.db.close()
    def reopen(self):
        learn=self.learn;budget=int(self.meta('initial_budget'))
        self.close()
        self.__init__(self.path,learn=learn,budget=budget,create=False)

    def _append(self,kind,body):
        # Enforce caller holds a sqlite write transaction before appending.
        require(self.db.in_transaction,'LEDGER_OUTSIDE_TX')
        last=self.db.execute('SELECT seq,seal FROM ledger ORDER BY seq DESC LIMIT 1').fetchone()
        seq=0 if last is None else last['seq']+1
        prev=GENESIS if last is None else last['seal']
        text=json.dumps(body,sort_keys=True,separators=(',',':'),allow_nan=False)
        seal=digest({'seq':seq,'kind':kind,'body':body,'prev':prev})
        self.db.execute('INSERT INTO ledger VALUES (?,?,?,?,?)',(seq,kind,text,prev,seal))
        return seal

    def choose(self,cue,issue_tick):
        require(type(cue) is int and cue in INITIAL,'BAD_CUE')
        require(type(issue_tick) is int and 0<=issue_tick<9000,'ISSUE_TICK')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row=self.db.execute('SELECT * FROM policy WHERE cue=?',(cue,)).fetchone()
            require(row is not None,'OWNER_POLICY_MISSING')
            did=self.db.execute('SELECT count(*) FROM decisions').fetchone()[0]
            choice=int(row['choice']);version=int(row['version'])
            pe_out=emit_single('C',0,0,choice,issue_tick)
            decision={'id':did,'cue':cue,'choice':choice,'version':version,
                      'issue_tick':issue_tick,'C_emit':list(pe_out['emissions'])}
            decision['decision_sha256']=digest(decision)
            self.db.execute('INSERT INTO decisions VALUES (?,?,?,?,?,?,?)',
                            (did,cue,choice,version,issue_tick,decision['decision_sha256'],'OPEN'))
            self._append('ISSUE',decision)
            self.db.execute('COMMIT');return copy.deepcopy(decision)
        except Exception:
            self.db.execute('ROLLBACK');raise

    def submit(self,env,arrival_tick):
        require(type(arrival_tick) is int and 0<=arrival_tick<10000,'ARRIVAL_TICK')
        require(type(env) is dict and set(env)=={'vote','vote_sha256','relay_channel','relay_sha256'},'ENVELOPE_SCHEMA')
        v=env['vote']
        require(type(v) is dict and set(v)=={'id','cue','version','issue_tick','receiver','decision_sha256',
                    'observed_raw','goal_raw','outcome','feedback_channel'},'VOTE_SCHEMA')
        require(type(v['id']) is int,'BAD_ID')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            dec=self.db.execute('SELECT * FROM decisions WHERE id=?',(v['id'],)).fetchone()
            require(dec is not None and dec['status']=='OPEN','NO_PENDING_OR_REPLAY')
            require(type(v['cue']) is int and v['cue']==dec['cue'] and type(v['version']) is int and
                v['version']==dec['version'] and type(v['issue_tick']) is int and v['issue_tick']==dec['issue_tick'] and
                v['decision_sha256']==dec['decision_sha'],'DECISION_BINDING')
            state=self.db.execute('SELECT * FROM policy WHERE cue=?',(dec['cue'],)).fetchone()
            require(dec['version']==state['version'],'OBSOLETE_POLICY_VERSION')
            require(dec['issue_tick']+3<=arrival_tick<=dec['issue_tick']+7,'EXPIRED_OR_PREMATURE')
            receiver=v['receiver'];require(type(receiver) is str and receiver in RECEIVERS,'BAD_RECEIVER')
            require(not self.db.execute('SELECT 1 FROM votes WHERE decision_id=? AND receiver=?',
                (v['id'],receiver)).fetchone(),'DUPLICATE_RECEIVER_VOTE')
            require(type(v['observed_raw']) is int and v['observed_raw'] in (5,11),'BAD_MEASUREMENT')
            require(type(v['goal_raw']) is int and v['goal_raw'] in (5,11),'BAD_GOAL')
            require(type(v['outcome']) is str and v['outcome'] in ('IMPROVED','WORSENED'),'BAD_OUTCOME')
            ch=FEEDBACK_CHANNEL[(receiver,v['outcome'])]
            require(v['feedback_channel']==ch,'CHANNEL_OUTCOME_MISMATCH')
            require(env['vote_sha256']==digest(v),'VOTE_DIGEST_DRIFT')
            require(type(env['relay_channel']) is int and env['relay_channel']==ch+10,'RELAY_CHANNEL_DRIFT')
            require(env['relay_sha256']==digest({'vote_sha256':env['vote_sha256'],
                'relay_channel':env['relay_channel']}),'RELAY_DIGEST_DRIFT')
            arrival=emit_single('C-return-'+receiver,env['relay_channel'],env['relay_channel'],ch+20,arrival_tick)
            require(arrival['emissions']==(ch+20,),'C_RETURN_PE_NO_EMISSION')
            self.db.execute('INSERT INTO votes VALUES (?,?,?,?)',
                            (v['id'],receiver,v['outcome'],env['vote_sha256']))
            self._append('VOTE',{'id':v['id'],'receiver':receiver,'outcome':v['outcome'],
                                 'vote_sha':env['vote_sha256']})
            votes=self.db.execute('SELECT receiver,outcome FROM votes WHERE decision_id=?',(v['id'],)).fetchall()
            if len(votes)==1:
                self.db.execute('COMMIT');return 'RECEIVED'
            require({r['receiver'] for r in votes}==set(RECEIVERS),'QUORUM_DUPLICITY')
            outcomes=dict((r['receiver'],r['outcome']) for r in votes)
            a,b=(outcomes[r] for r in RECEIVERS)
            result='HELD'
            if a==b=='WORSENED' and self.learn and state['budget']>0:
                new_choice=11 if state['choice']==12 else 12
                cur=self.db.execute('UPDATE policy SET choice=?,version=version+1,budget=budget-1 '
                    'WHERE cue=? AND version=? AND budget>0',(new_choice,dec['cue'],dec['version']))
                require(cur.rowcount==1,'POLICY_CAS_REJECTED')
                result='UPDATED'
            elif a!=b:result='CONFLICT_HELD'
            elif a==b=='IMPROVED':result='IMPROVED_HELD'
            newver=self.db.execute('SELECT version FROM policy WHERE cue=?',(dec['cue'],)).fetchone()[0]
            transcript={'id':v['id'],'cue':dec['cue'],'votes':[a,b],'result':result,'policy_version_after':newver}
            self.db.execute("UPDATE decisions SET status='COMPLETE' WHERE id=? AND status='OPEN'",(v['id'],))
            self.db.execute('INSERT INTO results VALUES (?,?,?)',(v['id'],result,json.dumps(transcript,sort_keys=True)))
            self._append('SETTLE',transcript)
            self.db.execute('COMMIT');return result
        except Exception:
            self.db.execute('ROLLBACK');raise

    def close_batch(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            ids=[r[0] for r in self.db.execute("SELECT id FROM decisions WHERE status='OPEN' ORDER BY id")]
            for did in ids:
                self.db.execute("UPDATE decisions SET status='CLOSED' WHERE id=?",(did,))
                self._append('CLOSE',{'id':did})
            self.db.execute('COMMIT');return len(ids)
        except Exception:
            self.db.execute('ROLLBACK');raise

    def audit(self):
        """Replay *entire* ledger, check materialized P-state and custody tables.

        Detects accidental corruption and partial write; not malicious rollback,
        because the controlling host can construct a new internally valid DB.
        """
        events=self.db.execute('SELECT * FROM ledger ORDER BY seq').fetchall()
        require(len(events)>0,'MISSING_LEDGER')
        prev=GENESIS;policy={c:[v,0,int(self.meta('initial_budget'))] for c,v in INITIAL.items()}
        opened={};votes={};results={};closed=set()
        for seq,e in enumerate(events):
            require(e['seq']==seq and e['prev']==prev,'LEDGER_CHAIN_SEQUENCE')
            try:body=json.loads(e['body'])
            except (json.JSONDecodeError,TypeError):raise LoopBoundary('LEDGER_BODY_INVALID')
            require(e['seal']==digest({'seq':seq,'kind':e['kind'],'body':body,'prev':prev}),
                    'LEDGER_SEAL_DRIFT')
            prev=e['seal'];kind=e['kind']
            if kind=='INIT':
                require(seq==0 and body=={'owner':OWNER,'pe':PE_ID,'learn':self.learn,
                    'budget':int(self.meta('initial_budget'))},'LEDGER_INIT_DRIFT')
            elif kind=='ISSUE':
                c=body['cue'];did=body['id']
                require(did==len(opened) and c in INITIAL and body['choice']==policy[c][0] and
                    body['version']==policy[c][1] and body['C_emit']==[body['choice']],'LEDGER_BAD_ISSUE')
                require(body['decision_sha256']==digest({k:v for k,v in body.items() if k!='decision_sha256'}),'LEDGER_BAD_DECISION_HASH')
                opened[did]=body;votes[did]={}
            elif kind=='VOTE':
                did=body['id'];recv=body['receiver']
                require(did in opened and did not in results and did not in closed and
                    recv in RECEIVERS and recv not in votes[did] and body['outcome'] in ('IMPROVED','WORSENED') and
                    len(body['vote_sha'])==64,'LEDGER_BAD_VOTE')
                votes[did][recv]=(body['outcome'],body['vote_sha'])
            elif kind=='SETTLE':
                did=body['id'];c=body['cue']
                require(did in opened and did not in results and did not in closed and
                    c==opened[did]['cue'] and len(votes[did])==2 and
                    set(votes[did])==set(RECEIVERS),'LEDGER_BAD_SETTLE')
                a,b=(votes[did][r][0] for r in RECEIVERS)
                require(body['votes']==[a,b] and opened[did]['version']==policy[c][1],'LEDGER_SETTLE_STALE')
                expected='HELD'
                if a==b=='WORSENED' and self.learn and policy[c][2]>0:
                    expected='UPDATED';policy[c][0]=11 if policy[c][0]==12 else 12
                    policy[c][1]+=1;policy[c][2]-=1
                elif a!=b:expected='CONFLICT_HELD'
                elif a==b=='IMPROVED':expected='IMPROVED_HELD'
                require(body['result']==expected and body['policy_version_after']==policy[c][1],'LEDGER_WRONG_SETTLEMENT')
                results[did]=body
            elif kind=='CLOSE':
                did=body['id'];require(did in opened and did not in results and did not in closed,'LEDGER_BAD_CLOSE')
                closed.add(did)
            else:raise LoopBoundary('LEDGER_UNKNOWN_EVENT')
        material={r['cue']:[r['choice'],r['version'],r['budget']] for r in self.db.execute('SELECT * FROM policy')}
        require(material==policy,'MATERIALIZED_POLICY_DRIFT')
        rows=list(self.db.execute('SELECT * FROM decisions ORDER BY id'))
        require(len(rows)==len(opened),'MATERIALIZED_DECISION_COUNT')
        for r in rows:
            d=opened[r['id']]
            status='COMPLETE' if r['id'] in results else 'CLOSED' if r['id'] in closed else 'OPEN'
            require(r['cue']==d['cue'] and r['choice']==d['choice'] and r['version']==d['version'] and
                r['issue_tick']==d['issue_tick'] and r['decision_sha']==d['decision_sha256'] and
                r['status']==status,'MATERIALIZED_DECISION_DRIFT')
        vrows=list(self.db.execute('SELECT * FROM votes'))
        require(len(vrows)==sum(map(len,votes.values())),'MATERIALIZED_VOTE_COUNT')
        for r in vrows:
            require((r['outcome'],r['vote_sha'])==votes[r['decision_id']][r['receiver']], 'MATERIALIZED_VOTE_DRIFT')
        rs=list(self.db.execute('SELECT * FROM results'))
        require(len(rs)==len(results),'MATERIALIZED_RESULT_COUNT')
        for r in rs:
            require(r['result']==results[r['id']]['result'] and json.loads(r['transcript'])==results[r['id']],
                'MATERIALIZED_RESULT_DRIFT')
        return {'ledger_events':len(events),'ledger_tip':prev,'decisions':len(opened),
                'closed':len(closed),'settled':len(results),'votes':len(vrows),
                'updates':sum(r['result']=='UPDATED' for r in rs),
                'state_domain':'P','owner':OWNER,'pe_id':PE_ID,
                'state_digest':digest(material)}
