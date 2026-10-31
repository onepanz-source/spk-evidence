"""T8MNO: runtime-owned P authority IN THE NEW REFERENCE v1 implementation.

Real authorization/grant/commit code exists here (unlike T8's all-DENIED
contract candidate), but it is neither SPK native Memory Contract v0 nor a
trusted authority with respect to the privileged host.
"""
from __future__ import annotations
from pathlib import Path
import json,sqlite3
from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import check
from research.spk_v5_t6abc_def_ghi.loop_v0 import digest
from .semantic_bus_v1 import verify as verify_bus

INIT={0:12,1:11}
SCHEMA='spk-v1-reference-C-owned-P-authority/v1'
ZERO='0'*64

class PAuthorityV1:
    def __init__(self,path,*,learn=True,budget=12,create=True):
        check(type(learn) is bool and type(budget) is int and 0<=budget<=48,'P_POLICY_CONFIG')
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.learn=learn;self.budget=budget
        self.db=sqlite3.connect(str(self.path),isolation_level=None,timeout=10)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        if create:
            check(self.db.execute("SELECT name FROM sqlite_master WHERE name='metadata'").fetchone() is None,'P_ALREADY_INITIALIZED')
            self.db.executescript('''
                CREATE TABLE metadata(k TEXT PRIMARY KEY,v TEXT NOT NULL);
                CREATE TABLE p(cue INTEGER PRIMARY KEY,choice INTEGER NOT NULL,version INTEGER NOT NULL,budget INTEGER NOT NULL);
                CREATE TABLE issue(id INTEGER PRIMARY KEY,cue INTEGER NOT NULL,choice INTEGER NOT NULL,version INTEGER NOT NULL,goal INTEGER NOT NULL,status TEXT NOT NULL,source_sha TEXT,outcome TEXT);
                CREATE TABLE grant(ident INTEGER PRIMARY KEY,issue_id INTEGER NOT NULL UNIQUE,owner TEXT NOT NULL,domain TEXT NOT NULL,mode TEXT NOT NULL,expected_version INTEGER NOT NULL,receipt_sha TEXT NOT NULL,consumed INTEGER NOT NULL);
                CREATE TABLE ledger(seq INTEGER PRIMARY KEY,kind TEXT NOT NULL,payload TEXT NOT NULL,previous TEXT NOT NULL,hash TEXT NOT NULL);
            ''')
            self.db.execute('BEGIN IMMEDIATE')
            try:
                for k,v in {'schema':SCHEMA,'owner':'C','pe_id':'PE-C-REFERENCE-V1','domain':'P',
                    'mode':'execute','learn':str(int(learn)),'budget':str(budget)}.items():
                    self.db.execute('INSERT INTO metadata VALUES(?,?)',(k,v))
                for cue,choice in sorted(INIT.items()):
                    self.db.execute('INSERT INTO p VALUES(?,?,0,?)',(cue,choice,budget))
                self._event('INIT',{'initial':INIT,'learn':learn,'budget':budget})
                self.db.execute('COMMIT')
            except BaseException:self.db.execute('ROLLBACK');raise
        else:
            expected={'schema':SCHEMA,'owner':'C','pe_id':'PE-C-REFERENCE-V1','domain':'P',
                    'mode':'execute','learn':str(int(learn)),'budget':str(budget)}
            check(dict(self.db.execute('SELECT k,v FROM metadata'))==expected,'REOPEN_METADATA_DRIFT')
            self.audit()

    def close(self):self.db.close()
    def reopen(self):
        self.close();self.__init__(self.path,learn=self.learn,budget=self.budget,create=False)

    def _event(self,kind,payload):
        check(self.db.in_transaction,'LEDGER_NONATOMIC')
        prev=self.db.execute('SELECT * FROM ledger ORDER BY seq DESC LIMIT 1').fetchone()
        n=prev['seq']+1 if prev else 0;old=prev['hash'] if prev else ZERO
        h=digest({'n':n,'kind':kind,'payload':payload,'prev':old})
        self.db.execute('INSERT INTO ledger VALUES(?,?,?,?,?)',
            (n,kind,json.dumps(payload,sort_keys=True,separators=(',',':')),old,h))

    @property
    def policy(self):return {r['cue']:r['choice'] for r in self.db.execute('SELECT * FROM p')}
    @property
    def versions(self):return {r['cue']:r['version'] for r in self.db.execute('SELECT * FROM p')}

    def issue(self,cue,goal):
        check(type(cue) is int and cue in INIT and type(goal) is int and goal in (11,12),'P_ISSUE_DOMAIN')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            check(self.db.execute("SELECT COUNT(*) FROM issue WHERE status='OPEN'").fetchone()[0]==0,'P_OPEN_DECISION')
            p=self.db.execute('SELECT * FROM p WHERE cue=?',(cue,)).fetchone()
            ident=self.db.execute('SELECT COUNT(*) FROM issue').fetchone()[0]
            d={'id':ident,'cue':cue,'choice':p['choice'],'version':p['version'],'goal':goal}
            self.db.execute("INSERT INTO issue(id,cue,choice,version,goal,status) VALUES(?,?,?,?,?,'OPEN')",
                            (ident,cue,p['choice'],p['version'],goal))
            self._event('ISSUE',d)
            self.db.execute('COMMIT');return d
        except BaseException:self.db.execute('ROLLBACK');raise

    def unsettled(self):
        return [dict(x) for x in self.db.execute("SELECT id,cue,choice,version,goal FROM issue WHERE status='OPEN'")]

    def settle(self,issue,source,packet,*,drop=False):
        # Reconstruct the entire reference v1 bus from original frozen source,
        # not trusting an outcome or grant supplied by an external caller.
        check(type(issue) is dict and set(issue)=={'id','cue','choice','version','goal'},'ISSUE_SCHEMA')
        verified=verify_bus(source,issue,packet,drop=drop)
        outcome='ABSENT' if drop else verified['payload']['verdict']
        check(outcome in ('ABSENT','IMPROVED','WORSENED'),'OUTCOME_DOMAIN')
        sha=digest(source);receipt_sha=digest(verified) if verified else None
        self.db.execute('BEGIN IMMEDIATE')
        try:
            r=self.db.execute('SELECT * FROM issue WHERE id=?',(issue['id'],)).fetchone()
            check(r is not None and r['status']=='OPEN' and
                all(r[k]==issue[k] for k in issue),'P_STALE_OR_REPLAY')
            state=self.db.execute('SELECT * FROM p WHERE cue=?',(r['cue'],)).fetchone()
            check(state['choice']==issue['choice'] and state['version']==issue['version'],'P_VERSION_DRIFT')
            is_negative=outcome=='WORSENED'
            eligible=bool(self.learn and is_negative and state['budget']>0 and verified is not None)
            granted=None
            if eligible:
                n=self.db.execute('SELECT COUNT(*) FROM grant').fetchone()[0]
                granted={'grant_id':n,'issue_id':r['id'],'owner':'C','domain':'P','mode':'execute',
                    'expected_version':state['version'],'receipt_digest':receipt_sha}
                self.db.execute('INSERT INTO grant VALUES(?,?,?,?,?,?,?,1)',
                    (n,r['id'],'C','P','execute',state['version'],receipt_sha))
                self._event('GRANT',granted)
                count=self.db.execute('UPDATE p SET choice=?,version=version+1,budget=budget-1 WHERE cue=? AND version=?',
                    (11 if state['choice']==12 else 12,r['cue'],state['version'])).rowcount
                check(count==1,'P_CAS_FAILED')
            result={'issue_id':r['id'],'cue':r['cue'],'choice_before':r['choice'],
                'version_before':r['version'],'outcome':outcome,'source_sha256':sha,
                'receipt_digest':receipt_sha,'grant_id':granted['grant_id'] if granted else None,
                'P_written':eligible,'choice_after':self.db.execute('SELECT choice FROM p WHERE cue=?',(r['cue'],)).fetchone()[0]}
            self.db.execute("UPDATE issue SET status='SETTLED',source_sha=?,outcome=? WHERE id=?",(sha,outcome,r['id']))
            self._event('SETTLE',result)
            self.db.execute('COMMIT')
            return result
        except BaseException:self.db.execute('ROLLBACK');raise

    def audit(self):
        # Reconstruct materialized P, version, budget, issue and grants from an
        # independently checked ledger. Complete privileged host reseal remains possible.
        logs=list(self.db.execute('SELECT * FROM ledger ORDER BY seq'))
        check(len(logs)>0,'LEDGER_EMPTY')
        p={c:[v,0,self.budget] for c,v in INIT.items()}
        decisions={};settled={};grants={};prev=ZERO
        for n,r in enumerate(logs):
            check(r['seq']==n and r['previous']==prev,'LEDGER_LINK_DRIFT')
            try:body=json.loads(r['payload'])
            except (ValueError,TypeError):check(False,'LEDGER_JSON')
            check(r['hash']==digest({'n':n,'kind':r['kind'],'payload':body,'prev':prev}),'LEDGER_HASH_DRIFT')
            prev=r['hash']
            if r['kind']=='INIT':
                check(n==0 and body=={'initial':{'0':12,'1':11},'learn':self.learn,'budget':self.budget},'LEDGER_INIT')
            elif r['kind']=='ISSUE':
                c=body['cue'];i=body['id']
                check(i==len(decisions) and i not in decisions and c in p and
                    body['choice']==p[c][0] and body['version']==p[c][1] and body['goal'] in (11,12) and
                    len(decisions)==len(settled),'LEDGER_ISSUE_DRIFT')
                decisions[i]=body
            elif r['kind']=='GRANT':
                i=body['issue_id'];c=decisions[i]['cue'];num=body['grant_id']
                check(i in decisions and i not in settled and i not in (x['issue_id'] for x in grants.values()) and
                    num==len(grants) and body['owner']=='C' and body['domain']=='P' and body['mode']=='execute' and
                    body['expected_version']==p[c][1] and self.learn and p[c][2]>0 and
                    type(body['receipt_digest']) is str and len(body['receipt_digest'])==64,'LEDGER_GRANT_DRIFT')
                grants[num]=body
            elif r['kind']=='SETTLE':
                i=body['issue_id'];check(i in decisions and i not in settled,'LEDGER_SETTLE_DRIFT')
                d=decisions[i];c=d['cue'];eligible=body['outcome']=='WORSENED' and self.learn and p[c][2]>0
                check(body['cue']==c and body['choice_before']==p[c][0] and body['version_before']==p[c][1] and
                    body['source_sha256'] and len(body['source_sha256'])==64 and
                    body['outcome'] in ('IMPROVED','WORSENED','ABSENT'),'LEDGER_SOURCE_DRIFT')
                check((body['outcome']=='IMPROVED')==(d['choice']==d['goal']) if body['outcome']!='ABSENT' else True,
                      'LEDGER_OUTCOME_BINDING')
                if eligible:
                    check(body['grant_id'] is not None and body['grant_id'] in grants and
                        grants[body['grant_id']]['issue_id']==i and
                        grants[body['grant_id']]['receipt_digest']==body['receipt_digest'] and
                        body['P_written'] is True,'LEDGER_MISSING_GRANT')
                    p[c][0]=11 if p[c][0]==12 else 12;p[c][1]+=1;p[c][2]-=1
                else:check(body['grant_id'] is None and body['P_written'] is False,'LEDGER_PHANTOM_GRANT')
                check(body['choice_after']==p[c][0],'LEDGER_CHOICE_DRIFT')
                settled[i]=body
            else:check(False,'LEDGER_UNSUPPORTED_EVENT')
        check({r['cue']:[r['choice'],r['version'],r['budget']] for r in self.db.execute('SELECT * FROM p')}==p,'P_MATERIAL_DRIFT')
        actual=list(self.db.execute('SELECT * FROM issue ORDER BY id'))
        check(len(actual)==len(decisions),'ISSUE_COUNT_DRIFT')
        for r in actual:
            d=decisions[r['id']];check(all(r[k]==v for k,v in d.items()),'ISSUE_MATERIAL_DRIFT')
            check(r['status']==('SETTLED' if r['id'] in settled else 'OPEN'),'ISSUE_STATUS_DRIFT')
            if r['id'] in settled:
                check(r['source_sha']==settled[r['id']]['source_sha256'] and r['outcome']==settled[r['id']]['outcome'],'ISSUE_SETTLE_DRIFT')
            else:check(r['source_sha'] is None and r['outcome'] is None,'ISSUE_PENDING_DRIFT')
        material=list(self.db.execute('SELECT * FROM grant ORDER BY ident'))
        check(len(material)==len(grants),'GRANT_COUNT_DRIFT')
        check({g['issue_id'] for g in grants.values()}==
            {i for i,x in settled.items() if x['P_written']},'GRANT_SETTLEMENT_MISMATCH')
        for r in material:
            g=grants[r['ident']]
            check(r['issue_id']==g['issue_id'] and r['owner']==g['owner'] and r['domain']==g['domain'] and
                r['mode']==g['mode'] and r['expected_version']==g['expected_version'] and
                r['receipt_sha']==g['receipt_digest'] and r['consumed']==1,'GRANT_MATERIAL_DRIFT')
        return {'episodes':len(actual),'settled':len(settled),'pending':len(decisions)-len(settled),
            'reference_grants':len(grants),'reference_P_writes':len(grants),
            'policy':self.policy,'versions':self.versions,'ledger_events':len(logs),'ledger_tip':prev}
