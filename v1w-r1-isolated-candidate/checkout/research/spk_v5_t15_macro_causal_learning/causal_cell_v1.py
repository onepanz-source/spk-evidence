"""T15 research: prospective causal-feedback falsification with original SPK PE primitive.

Thermal world evolves before any A verdict. A and C are distinct computational
actors; the host supplies raw stimulus and world setpoint, never a verdict or
per-trial desired action. One monotone action rule is assumed by C's update.
This is a *new* experimental loop, not original SPK BV, original P custody,
independent hardware attestation, or general reinforcement learning.
"""
from __future__ import annotations
import hashlib, json, sqlite3
from pathlib import Path
from types import SimpleNamespace
from spk_architecture_v1.pe_execution_v1b import _compute_local

SCHEMA='spk-v5-t15-prospective-thermal-PE-judgment/research-v0'
STATE_BITS=16
MAX_TEMP=15
HEAT,COOL=11,12

def ensure(condition, code):
    if not condition: raise ValueError(code)

def encode(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)

def sha(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()

def pe_eval(instructions,channels,tick=10):
    n=SimpleNamespace(instructions=tuple(instructions),state_bits=STATE_BITS,fractional_bits=0)
    raw,guard,emits=_compute_local(n,(0,0),tick,tuple(channels))
    return {'raw':raw,'guard':guard,'emits':list(emits)}

class ThermalWorld:
    """Environment/plant knows equilibrium; it never constructs a feedback label."""
    def __init__(self,setpoint,*,reverse_actuator=False):
        ensure(type(reverse_actuator) is bool,'WORLD_REVERSE_MODE')
        self.reverse_actuator=reverse_actuator
        ensure(type(setpoint) is int and 3<=setpoint<=12,'WORLD_SETPOINT')
        self.setpoint=setpoint
    def apply(self,temperature,choice):
        ensure(type(temperature) is int and 0<=temperature<=MAX_TEMP,'WORLD_TEMPERATURE')
        ensure(choice in (HEAT,COOL),'WORLD_ACTION')
        return min(MAX_TEMP,max(0,temperature+((1 if choice==HEAT else -1)*(-1 if self.reverse_actuator else 1))))

class CNeuron:
    """C decides with two complementary original PE computations; P owns theta."""
    @staticmethod
    def choose(temperature,theta):
        ensure(type(temperature) is int and 0<=temperature<=MAX_TEMP,'C_TEMPERATURE')
        ensure(type(theta) is int and 1<=theta<=16,'C_P_RANGE')
        # Cold: 16-temperature >= 17-theta  <=> temperature < theta.
        cold=pe_eval((('ACC',(1,1)),('CMP',17-theta),('EMIT',HEAT)),[1]*(16-temperature))
        hot=pe_eval((('ACC',(1,1)),('CMP',theta),('EMIT',COOL)),[1]*temperature)
        emitted=cold['emits']+hot['emits']
        ensure(len(emitted)==1,'C_PE_DECISION_AMBIGUOUS')
        return emitted[0],sha({'theta':theta,'temperature':temperature,'cold':cold,'hot':hot})
    @staticmethod
    def propose(theta,temperature,choice,verdict):
        ensure(verdict in ('IMPROVED','WORSENED','NEUTRAL'),'C_INVALID_VERDICT')
        if verdict!='WORSENED':return theta
        # Credit rule assumes monotone signed actuation. A supplies only a
        # comparison, NOT the target, correct action or desired theta.
        return min(theta,temperature) if choice==HEAT else max(theta,temperature+1)

class ANeuron:
    """A locally derives features from *post-action sensor readings*, then uses
    actual frozen SPK PE threshold/EMIT to judge whether the world improved.
    The absolute-distance encoding is Python-owned A preprocessing, not PE IR.
    """
    @staticmethod
    def judge(before,after,setpoint):
        ensure(all(type(x) is int and 0<=x<=MAX_TEMP for x in (before,after,setpoint)),
               'A_SENSOR_DOMAIN')
        old_distance=abs(before-setpoint)
        new_distance=abs(after-setpoint)
        # Two independent PE decisions; no host-supplied reward/verdict.
        imp=pe_eval((('ACC',(1,1)),('ACC',(1,2)),('CMP',17),('EMIT',21)),
                    [1]*old_distance+[2]*(16-new_distance),12)
        wors=pe_eval((('ACC',(1,1)),('ACC',(1,2)),('CMP',17),('EMIT',22)),
                     [1]*new_distance+[2]*(16-old_distance),12)
        emissions=imp['emits']+wors['emits']
        ensure(emissions in ([21],[22],[]),'A_PE_CONFLICT')
        verdict=('IMPROVED' if emissions==[21] else
                 'WORSENED' if emissions==[22] else 'NEUTRAL')
        return {'verdict':verdict,'emissions':emissions,
                'PE_digest':sha({'improve':imp,'worsen':wors}),
                'measurement_digest':sha({'before':before,'after':after,'setpoint':setpoint}),
                'preprocessing':'A_LOCAL_ABSOLUTE_DISTANCE_ENCODER_V1'}

class BRelay:
    @staticmethod
    def forward(episode,verdict,proof):
        ensure(verdict in ('IMPROVED','WORSENED','NEUTRAL'),'B_VERDICT_DOMAIN')
        # A control event still passes through B's original PE fragment.
        signal=21 if verdict=='IMPROVED' else 22 if verdict=='WORSENED' else 23
        pe=pe_eval((('ACC',(1,signal)),('CMP',1),('EMIT',31)),[signal],13)
        ensure(pe['emits']==[31],'B_PE_FORWARD_FAILURE')
        return {'episode':episode,'verdict':verdict,'A_digest':sha(proof),
                'B_PE_digest':sha(pe),'relay_channel':31}

class LearningCell:
    """Durable single-cell causal loop, one atomic SQL transaction per episode.

    Separate calls for observe/forward/learn may be an architectural extension.
    Here the entire episode is atomic: no fake claims of distinct processes or
    physical tick scheduling. C can only update after A and B records exist.
    """
    def __init__(self,path,*,setpoint,theta=12,create=True,reverse_actuator=False):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.world=ThermalWorld(setpoint,reverse_actuator=reverse_actuator)
        self.db=sqlite3.connect(str(self.path),isolation_level=None,timeout=10)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        if create:
            ensure(self.db.execute("SELECT name FROM sqlite_master WHERE name='config'").fetchone() is None,
                   'CELL_ALREADY_INITIALIZED')
            self.db.executescript('''
            CREATE TABLE config(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE p(singleton INTEGER PRIMARY KEY CHECK(singleton=1),theta INTEGER NOT NULL,
                           version INTEGER NOT NULL,commit_count INTEGER NOT NULL);
            CREATE TABLE episode(id INTEGER PRIMARY KEY,temperature INTEGER NOT NULL,
                           choice INTEGER NOT NULL,after_temperature INTEGER NOT NULL,
                           verdict TEXT,phase TEXT NOT NULL, P_version_read INTEGER NOT NULL,
                           P_version_end INTEGER NOT NULL,grant INTEGER NOT NULL,source_digest TEXT NOT NULL);
            CREATE TABLE event(id INTEGER PRIMARY KEY,episode_id INTEGER NOT NULL,
                           kind TEXT NOT NULL,payload_json TEXT NOT NULL,digest TEXT NOT NULL);
            CREATE TABLE p_credit(episode_id INTEGER PRIMARY KEY,expected_version INTEGER NOT NULL,
                           next_version INTEGER NOT NULL,old_theta INTEGER NOT NULL,
                           new_theta INTEGER NOT NULL,source_digest TEXT NOT NULL);
            ''')
            for k,v in {'schema':SCHEMA,'setpoint':setpoint,'world_law':'HEAT_MINUS_ONE_COOL_PLUS_ONE' if reverse_actuator else 'HEAT_PLUS_ONE_COOL_MINUS_ONE',
                        'mode':'RESEARCH','initial_theta':str(theta),'frozen_SPK_P_learning':'FALSE'}.items():
                self.db.execute('INSERT INTO config VALUES(?,?)',(k,str(v)))
            self.db.execute('INSERT INTO p VALUES(1,?,0,0)',(theta,))
        else:
            ensure(dict(self.db.execute('SELECT key,value FROM config'))==
                   {'schema':SCHEMA,'setpoint':str(setpoint),'world_law':'HEAT_MINUS_ONE_COOL_PLUS_ONE' if reverse_actuator else 'HEAT_PLUS_ONE_COOL_MINUS_ONE',
                    'mode':'RESEARCH','initial_theta':str(theta),'frozen_SPK_P_learning':'FALSE'},'CELL_CONFIG_MISMATCH')
            self.audit()
    def close(self):self.db.close()
    def reopen(self):
        self.close();self.__init__(self.path,setpoint=self.world.setpoint,create=False,
                                   reverse_actuator=self.world.reverse_actuator)
    def _event(self,episode,kind,body):
        ensure(self.db.in_transaction,'EVENT_OUTSIDE_TRANSACTION')
        eid=self.db.execute('SELECT COUNT(*) FROM event').fetchone()[0]
        stamp=sha({'id':eid,'episode':episode,'kind':kind,'body':body})
        self.db.execute('INSERT INTO event VALUES(?,?,?,?,?)',(eid,episode,kind,encode(body),stamp))
        return stamp
    def trial(self,temperature,*,learning=True,feedback='genuine'):
        ensure(type(temperature) is int and 0<=temperature<=MAX_TEMP,'TRIAL_TEMPERATURE')
        ensure(type(learning) is bool,'TRIAL_LEARNING_MODE')
        ensure(feedback in ('genuine','missing','wrong_lineage','altered'),'TRIAL_FEEDBACK_MODE')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            p=self.db.execute('SELECT * FROM p WHERE singleton=1').fetchone()
            before_theta,version=p['theta'],p['version']
            choice,c_pe=CNeuron.choose(temperature,before_theta)
            ep=self.db.execute('SELECT COUNT(*) FROM episode').fetchone()[0]
            after=self.world.apply(temperature,choice)
            # A learns the world target from its local sensor context, not an
            # oracle-provided right answer for this episode.
            a=ANeuron.judge(temperature,after,self.world.setpoint)
            self._event(ep,'C_PE_DECISION',{'choice':choice,'input_temperature':temperature,'P_version':version,'PE_digest':c_pe})
            self._event(ep,'WORLD_TRANSITION',{'before':temperature,'after':after,'actuation':choice})
            a_digest=self._event(ep,'A_PE_ASSESSMENT',a)
            relay=BRelay.forward(ep,a['verdict'],a)
            transmitted=dict(relay)
            if feedback=='wrong_lineage':
                transmitted['episode']=ep+1
            elif feedback=='altered':
                transmitted['verdict']=('IMPROVED' if a['verdict']!='IMPROVED' else 'WORSENED')
            self._event(ep,'B_PE_RELAY',transmitted)
            verdict=a['verdict']
            expected=BRelay.forward(ep,verdict,a)
            accepted=(feedback!='missing' and transmitted==expected)
            if not accepted:
                reason=('FEEDBACK_LOST' if feedback=='missing' else
                        'EVENT_LINEAGE_MISMATCH' if transmitted['episode']!=ep else
                        'A_PE_VERDICT_OR_DIGEST_MISMATCH')
                self._event(ep,'FEEDBACK_LOST' if feedback=='missing' else 'REJECTED_FEEDBACK',
                            {'reason':reason})
            proposal=CNeuron.propose(before_theta,temperature,choice,verdict) if accepted else before_theta
            grant=int(bool(learning and accepted and proposal!=before_theta))
            if grant:
                self.db.execute('UPDATE p SET theta=?,version=version+1,commit_count=commit_count+1 '
                                'WHERE singleton=1 AND theta=? AND version=?',
                                (proposal,before_theta,version))
                ensure(self.db.execute('SELECT changes()').fetchone()[0]==1,'P_CAS_FAILURE')
                self.db.execute('INSERT INTO p_credit VALUES(?,?,?,?,?,?)',
                                (ep,version,version+1,before_theta,proposal,a_digest))
                self._event(ep,'C_P_CREDIT',{'expected_version':version,'next_version':version+1,
                                           'theta_before':before_theta,'theta_after':proposal,
                                           'A_event_digest':a_digest})
            self.db.execute('INSERT INTO episode VALUES(?,?,?,?,?,?,?,?,?,?)',
                            (ep,temperature,choice,after,verdict,
                             'TRAIN' if learning else 'EVALUATE',version,version+grant,
                             grant,a_digest))
            self.db.execute('COMMIT')
            return {'episode':ep,'before':temperature,'after':after,'choice':choice,
                    'verdict':verdict,'credit':grant,'P_before':before_theta,'P_after':proposal,
                    'P_version_read':version,'A_event_digest':a_digest,
                    'improved':abs(after-self.world.setpoint)<abs(temperature-self.world.setpoint)}
        except BaseException:
            self.db.execute('ROLLBACK');raise
    def state(self):
        r=self.db.execute('SELECT theta,version,commit_count FROM p WHERE singleton=1').fetchone()
        return dict(r)
    def audit(self):
        es=[dict(x) for x in self.db.execute('SELECT * FROM episode ORDER BY id')]
        credits=[dict(x) for x in self.db.execute('SELECT * FROM p_credit ORDER BY episode_id')]
        events=[dict(x) for x in self.db.execute('SELECT * FROM event ORDER BY id')]
        for ev in events:
            body=json.loads(ev['payload_json'])
            ensure(ev['digest']==sha({'id':ev['id'],'episode':ev['episode_id'],'kind':ev['kind'],'body':body}),
                   'EVENT_DIGEST_TAMPER')
        versions=[];old=0;theta=int(dict(self.db.execute('SELECT key,value FROM config'))['initial_theta'])
        for ep in es:
            ensure(ep['id']==len(versions) and ep['P_version_read']==old and
                   ep['P_version_end']==old+ep['grant'],'EPISODE_VERSION_DRIFT')
            e=[x for x in events if x['episode_id']==ep['id']]
            bykind={x['kind']:x for x in e}
            ensure(all(x in bykind for x in ('C_PE_DECISION','WORLD_TRANSITION','A_PE_ASSESSMENT','B_PE_RELAY')),
                   'EPISODE_EVENT_GAP')
            ensure(sha(json.loads(bykind['A_PE_ASSESSMENT']['payload_json']))==
                   sha(ANeuron.judge(ep['temperature'],ep['after_temperature'],self.world.setpoint)),
                   'A_PE_REPLAY_MISMATCH')
            ensure(bykind['A_PE_ASSESSMENT']['digest']==ep['source_digest'],'EPISODE_A_CUSTODY_DRIFT')
            decision=json.loads(bykind['C_PE_DECISION']['payload_json'])
            world=json.loads(bykind['WORLD_TRANSITION']['payload_json'])
            predicted,pedigree=CNeuron.choose(ep['temperature'],theta)
            ensure(decision=={'choice':predicted,'input_temperature':ep['temperature'],
                              'P_version':old,'PE_digest':pedigree} and ep['choice']==predicted,
                   'C_DECISION_RECONSTRUCTION_FAILURE')
            ensure(world=={'before':ep['temperature'],'after':ep['after_temperature'],
                           'actuation':ep['choice']} and
                   ep['after_temperature']==self.world.apply(ep['temperature'],ep['choice']),
                   'WORLD_RECONSTRUCTION_FAILURE')
            assessment=json.loads(bykind['A_PE_ASSESSMENT']['payload_json'])
            received=json.loads(bykind['B_PE_RELAY']['payload_json'])
            expected=BRelay.forward(ep['id'],ep['verdict'],assessment)
            corrupted=received!=expected
            ensure(ep['verdict']==assessment['verdict'] and
                   (not corrupted or 'REJECTED_FEEDBACK' in bykind) and
                   (not ('REJECTED_FEEDBACK' in bykind) or corrupted),
                   'AB_FEEDBACK_RECONSTRUCTION_FAILURE')
            proposed=CNeuron.propose(theta,ep['temperature'],ep['choice'],ep['verdict'])
            excluded={'REJECTED_FEEDBACK','FEEDBACK_LOST'} & set(bykind)
            ensure(not ep['grant'] or (ep['phase']=='TRAIN' and not excluded and proposed!=theta),
                   'UNAUTHORIZED_C_P_CREDIT')
            if ep['grant']:
                ensure(any(c['episode_id']==ep['id'] and c['old_theta']==theta and
                           c['new_theta']==proposed for c in credits), 'CREDIT_THETA_DRIFT')
                theta=proposed
            if ep['grant']:
                ensure('C_P_CREDIT' in bykind,'CREDIT_NO_EVENT')
            old=ep['P_version_end'];versions.append(ep['id'])
        ensure(self.state()['theta']==theta,'P_THETA_RECONSTRUCTION_FAILURE')
        ensure(self.state()['version']==len(credits)==sum(x['grant'] for x in es),'P_VERSION_COUNT_DRIFT')
        ensure(self.state()['commit_count']==len(credits),'P_COMMIT_COUNT_DRIFT')
        for c in credits:
            ep=es[c['episode_id']]
            ensure(c['expected_version']==ep['P_version_read'] and
                   c['next_version']==ep['P_version_end'] and
                   c['source_digest']==ep['source_digest'],'CREDIT_CUSTODY_DRIFT')
        return {'epochs':len(es),'credits':len(credits),'events':len(events),
                'theta':self.state()['theta'],'P_version':old,
                'source_rows_sha256':sha(es),'event_rows_sha256':sha(events),
                'original_SPK_BV_learning':False,'original_SPK_P_grants':0}
