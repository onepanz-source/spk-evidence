"""T17: durable A-computed action-law discovery plus C threshold learning.

The actor-specific computation uses T15's actual frozen SPK PE primitive.
Each dispatch is one SQLite transaction. The dynamic is a deterministic test
world, not a native SPK BV scheduler, authenticated sensor or physical PE clock.
Host chooses stimuli/world; A's PE outcome cannot be supplied by the host.
"""
from __future__ import annotations
import json, sqlite3
from pathlib import Path
from research.spk_v5_t15_macro_causal_learning.causal_cell_v1 import (
  ThermalWorld,CNeuron,ANeuron,BRelay,HEAT,COOL,pe_eval,encode,sha,ensure)

SCHEMA='spk-v5-t17-staged-unknown-actuator-direction/research-v0'
STAGES=('C_PE','WORLD','A_PE','B_RELAY','C_CREDIT')
POLICY_SCHEMA='''CREATE TABLE policy(owner TEXT NOT NULL CHECK(owner='C'),domain TEXT NOT NULL CHECK(domain='P'),
 mode TEXT NOT NULL CHECK(mode IN ('execute','verify')),ceiling INTEGER NOT NULL CHECK(ceiling BETWEEN 0 AND 1000),
 revision INTEGER NOT NULL CHECK(revision>=0),singleton INTEGER PRIMARY KEY CHECK(singleton=1))'''
P_SCHEMA='''CREATE TABLE p(singleton INTEGER PRIMARY KEY CHECK(singleton=1),theta INTEGER NOT NULL,
 actuator_sign INTEGER NOT NULL CHECK(actuator_sign IN (-1,0,1)),
 version INTEGER NOT NULL CHECK(version>=0),commits INTEGER NOT NULL CHECK(commits>=0))'''
EP_SCHEMA='''CREATE TABLE episode(id INTEGER PRIMARY KEY,temperature INTEGER NOT NULL,learning INTEGER NOT NULL,
 transport TEXT NOT NULL,stage TEXT NOT NULL,P_version_read INTEGER,theta_read INTEGER,
 choice INTEGER,logical_choice INTEGER,sign_read INTEGER,choice_PE_sha TEXT,after_temp INTEGER,A_json TEXT,A_digest TEXT,B_json TEXT,
 verdict TEXT,credit INTEGER NOT NULL DEFAULT 0,P_version_end INTEGER,reason TEXT)'''
EV_SCHEMA='''CREATE TABLE pending(id INTEGER PRIMARY KEY,episode_id INTEGER NOT NULL,kind TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('QUEUED','DONE')),UNIQUE(episode_id,kind))'''
LOG_SCHEMA='''CREATE TABLE event(id INTEGER PRIMARY KEY,episode_id INTEGER NOT NULL,kind TEXT NOT NULL,
 body TEXT NOT NULL,digest TEXT NOT NULL)'''
GRANT_SCHEMA='''CREATE TABLE p_grant(episode_id INTEGER PRIMARY KEY,event_id INTEGER NOT NULL UNIQUE,
 expected_version INTEGER NOT NULL,new_version INTEGER NOT NULL,
 old_theta INTEGER NOT NULL,new_theta INTEGER NOT NULL,old_sign INTEGER NOT NULL,new_sign INTEGER NOT NULL,A_event_digest TEXT NOT NULL,
 authority_revision INTEGER NOT NULL,grant_digest TEXT NOT NULL)'''
INTENT_SCHEMA='''CREATE TABLE p_intent(singleton INTEGER PRIMARY KEY CHECK(singleton=1),
 episode_id INTEGER NOT NULL,expected_version INTEGER NOT NULL,old_theta INTEGER NOT NULL,
 new_theta INTEGER NOT NULL,old_sign INTEGER NOT NULL,new_sign INTEGER NOT NULL)'''
FENCE_SCHEMA='''CREATE TRIGGER p_update_guard BEFORE UPDATE ON p BEGIN
 SELECT RAISE(ABORT,'T17_NO_OWNED_P_INTENT') WHERE NOT EXISTS
 (SELECT 1 FROM p_intent i JOIN policy a ON a.singleton=1 WHERE i.singleton=1
 AND a.owner='C' AND a.domain='P' AND a.mode='execute'
 AND i.expected_version=OLD.version AND i.old_theta=OLD.theta
 AND i.new_theta=NEW.theta AND i.old_sign=OLD.actuator_sign
 AND i.new_sign=NEW.actuator_sign AND NEW.version=OLD.version+1
 AND NEW.commits=OLD.commits+1 AND
 (SELECT count(*) FROM p_grant)=OLD.commits);
END'''

def map_action(logical,polarity):
 """Unknown polarity 0 uses a probe of the default mapping; -1 swaps actuators."""
 ensure(logical in (HEAT,COOL) and polarity in (-1,0,1),'T17_ACTION_DOMAIN')
 return (COOL if logical==HEAT else HEAT) if polarity==-1 else logical

def judge_with_effect(before,after,setpoint):
 """A computes reward AND direction from readings via original SPK PE.

 The Python actor encodes distance and signed input channels. Original PE
 performs both threshold comparisons. No host-provided correct action.
 """
 a=ANeuron.judge(before,after,setpoint)
 positive=pe_eval((('ACC',(1,1)),('CMP',1),('EMIT',41)),[1]*max(0,after-before),12)
 negative=pe_eval((('ACC',(1,1)),('CMP',1),('EMIT',42)),[1]*max(0,before-after),12)
 ensure(not (positive['emits'] and negative['emits']),'T17_EFFECT_CONFLICT')
 sign=(1 if positive['emits'] else -1 if negative['emits'] else 0)
 result=dict(a)
 # Identify observed effect relative to the ACTUAL action at B, not at A.
 result.update({'effect_direction':sign,'effect_PE_digest':sha({'positive':positive,'negative':negative}),
                'effect_preprocessing':'A_LOCAL_SIGNED_SENSOR_DIFFERENCE_V1'})
 return result

def forward_with_effect(episode,a):
 """B relays PE reward and signed sensor direction; C infers actuator sign."""
 packet=BRelay.forward(episode,a['verdict'],a)
 return dict(packet,effect_direction=a['effect_direction'],effect_PE_digest=a['effect_PE_digest'])

def propose_P(theta,polarity,temperature,logical,a):
 # actual action determined from logical and polarity at observation time.
 observed=a['effect_direction']
 ensure(observed in (-1,0,1),'T17_EFFECT_INVALID')
 physical=map_action(logical,polarity)
 learned_sign=(observed * (1 if physical==HEAT else -1)) if observed else 0
 if learned_sign and polarity!=learned_sign:
  return theta,learned_sign
 if polarity!=0 and a['verdict']=='WORSENED':
  return CNeuron.propose(theta,temperature,logical,a['verdict']),polarity
 return theta,polarity

class StagedCell:
 def __init__(self,path,*,setpoint,theta=12,create=True,reverse_actuator=False,ceiling=16,max_active=3):
  self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
  self.world=ThermalWorld(setpoint,reverse_actuator=reverse_actuator)
  ensure(type(max_active) is int and 1<=max_active<=8,'ACTIVE_BUDGET_INVALID')
  self.max_active=max_active
  self.db=sqlite3.connect(str(self.path),timeout=15,isolation_level=None)
  self.db.row_factory=sqlite3.Row
  self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL')
  if create:
   ensure(self.db.execute("SELECT 1 FROM sqlite_master WHERE name='p'").fetchone() is None,'ALREADY_CREATED')
   for sql in (POLICY_SCHEMA,P_SCHEMA,EP_SCHEMA,EV_SCHEMA,LOG_SCHEMA,GRANT_SCHEMA,INTENT_SCHEMA,FENCE_SCHEMA):self.db.execute(sql)
   self.db.execute('CREATE TABLE config(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
   conf={'schema':SCHEMA,'setpoint':str(setpoint),'initial_theta':str(theta),
         'reverse_actuator':str(int(reverse_actuator)),'max_active':str(max_active),
         'original_SPK_learning':'FALSE'}
   for k,v in conf.items():self.db.execute('INSERT INTO config VALUES(?,?)',(k,v))
   self.db.execute('INSERT INTO p VALUES(1,?,0,0,0)',(theta,))
   ensure(type(ceiling) is int and 0<=ceiling<=1000,'CEILING_INVALID')
   self.db.execute("INSERT INTO policy VALUES('C','P','execute',?,0,1)",(ceiling,))
  else:
   conf=dict(self.db.execute('SELECT key,value FROM config'))
   ensure(conf=={'schema':SCHEMA,'setpoint':str(setpoint),'initial_theta':str(theta),
      'reverse_actuator':str(int(reverse_actuator)),'max_active':str(max_active),
      'original_SPK_learning':'FALSE'},'REOPEN_CONFIG_DRIFT')
   self.audit()
 def close(self):self.db.close()
 def reopen(self):
  init_theta=int(dict(self.db.execute('SELECT key,value FROM config'))['initial_theta'])
  self.close();self.__init__(self.path,setpoint=self.world.setpoint,theta=init_theta,create=False,
            reverse_actuator=self.world.reverse_actuator,max_active=self.max_active)
 def state(self):return dict(self.db.execute('SELECT theta,actuator_sign,version,commits FROM p').fetchone())
 def policy(self):return dict(self.db.execute('SELECT * FROM policy').fetchone())
 def _tx(self,fn):
  self.db.execute('BEGIN IMMEDIATE')
  try:
   result=fn();self.db.execute('COMMIT');return result
  except BaseException:
   self.db.execute('ROLLBACK');raise
 def set_policy(self,*,expected_revision,ceiling=None,mode=None):
  def fn():
   a=self.policy()
   ensure(a['revision']==expected_revision,'POLICY_REVISION_STALE')
   new_ceil=a['ceiling'] if ceiling is None else ceiling
   new_mode=a['mode'] if mode is None else mode
   ensure(type(new_ceil) is int and 0<=new_ceil<=1000 and new_ceil>=self.state()['commits'],'POLICY_BUDGET_INVALID')
   ensure(new_mode in ('execute','verify'),'POLICY_MODE_INVALID')
   self.db.execute('UPDATE policy SET mode=?,ceiling=?,revision=revision+1 WHERE singleton=1',(new_mode,new_ceil))
   return self.policy()
  return self._tx(fn)
 def submit(self,temperature,*,learning=True,feedback='genuine'):
  ensure(type(temperature) is int and 0<=temperature<=15,'INPUT_TEMP_INVALID')
  ensure(type(learning) is bool,'LEARN_MODE_INVALID')
  ensure(feedback in ('genuine','missing','altered','wrong_lineage','effect_tamper'),'FEEDBACK_MODE_INVALID')
  def fn():
   active=self.db.execute("SELECT count(*) FROM episode WHERE stage!='SETTLED'").fetchone()[0]
   ensure(active<self.max_active,'ACTIVE_EPOCH_CAPACITY')
   ep=self.db.execute('SELECT count(*) FROM episode').fetchone()[0]
   self.db.execute('INSERT INTO episode(id,temperature,learning,transport,stage) VALUES(?,?,?,? ,?)',
                   (ep,temperature,int(learning),feedback,'C_PE'))
   self.db.execute('INSERT INTO pending VALUES(NULL,?,?,?)',(ep,'C_PE','QUEUED'))
   return ep
  return self._tx(fn)
 def _log(self,ep,kind,body):
  eid=self.db.execute('SELECT count(*) FROM event').fetchone()[0]
  digest=sha({'id':eid,'episode':ep,'kind':kind,'body':body})
  self.db.execute('INSERT INTO event VALUES(?,?,?,?,?)',(eid,ep,kind,encode(body),digest))
  return eid,digest
 def _schedule(self,ep,kind):self.db.execute('INSERT INTO pending VALUES(NULL,?,?,?)',(ep,kind,'QUEUED'))
 def dispatch(self):
  def fn():
   q=self.db.execute("SELECT * FROM pending WHERE status='QUEUED' ORDER BY id LIMIT 1").fetchone()
   if q is None:return None
   ep=q['episode_id'];kind=q['kind'];e=self.db.execute('SELECT * FROM episode WHERE id=?',(ep,)).fetchone()
   ensure(e['stage']==kind,'STAGE_SEQUENCE_DRIFT')
   if kind=='C_PE':
    state=self.state()
    logical,pe=CNeuron.choose(e['temperature'],state['theta'])
    choice=map_action(logical,state['actuator_sign'])
    self.db.execute('UPDATE episode SET theta_read=?,sign_read=?,P_version_read=?,choice=?,logical_choice=?,choice_PE_sha=?,stage=? WHERE id=?',
                    (state['theta'],state['actuator_sign'],state['version'],choice,logical,pe,'WORLD',ep))
    self._log(ep,kind,{'temperature':e['temperature'],'choice':choice,'logical_choice':logical,
                       'actuator_sign':state['actuator_sign'],'theta':state['theta'],
                       'P_version':state['version'],'PE_digest':pe});self._schedule(ep,'WORLD')
   elif kind=='WORLD':
    after=self.world.apply(e['temperature'],e['choice'])
    self.db.execute('UPDATE episode SET after_temp=?,stage=? WHERE id=?',(after,'A_PE',ep))
    self._log(ep,kind,{'choice':e['choice'],'before':e['temperature'],'after':after});self._schedule(ep,'A_PE')
   elif kind=='A_PE':
    result=judge_with_effect(e['temperature'],e['after_temp'],self.world.setpoint)
    _,adigest=self._log(ep,kind,result)
    self.db.execute('UPDATE episode SET A_json=?,A_digest=?,verdict=?,stage=? WHERE id=?',
                    (encode(result),adigest,result['verdict'],'B_RELAY',ep));self._schedule(ep,'B_RELAY')
   elif kind=='B_RELAY':
    a=json.loads(e['A_json']);packet=forward_with_effect(ep,a)
    transmitted=dict(packet)
    if e['transport']=='altered':transmitted['verdict']='WORSENED' if a['verdict']!='WORSENED' else 'IMPROVED'
    elif e['transport']=='wrong_lineage':transmitted['episode']=ep+1
    elif e['transport']=='effect_tamper':transmitted['effect_direction']=(-a['effect_direction'] if a['effect_direction'] else 1)
    elif e['transport']=='missing':transmitted=None
    self._log(ep,kind,transmitted)
    self.db.execute('UPDATE episode SET B_json=?,stage=? WHERE id=?',
                    (encode(transmitted),'C_CREDIT',ep));self._schedule(ep,'C_CREDIT')
   elif kind=='C_CREDIT':
    # Replay the A computation independently from pre/post observations and the
    # ORIGINAL PE, then validate B's exact lineage. Host never supplies polarity.
    a=json.loads(e['A_json']);trans=json.loads(e['B_json'])
    expected_a=judge_with_effect(e['temperature'],e['after_temp'],self.world.setpoint)
    expected_b=forward_with_effect(ep,expected_a)
    proof=self.db.execute("SELECT id,body,digest FROM event WHERE episode_id=? AND kind='A_PE'",(ep,)).fetchone()
    ensure(a==expected_a and proof is not None and json.loads(proof['body'])==expected_a and
           proof['digest']==sha({'id':proof['id'],'episode':ep,'kind':'A_PE','body':expected_a}) and
           e['A_digest']==proof['digest'], 'A_EVENT_INTEGRITY_FAILURE')
    received=self.db.execute("SELECT id,body,digest FROM event WHERE episode_id=? AND kind='B_RELAY'",(ep,)).fetchone()
    ensure(received is not None and json.loads(received['body'])==trans and
           received['digest']==sha({'id':received['id'],'episode':ep,'kind':'B_RELAY','body':trans}),
           'B_EVENT_INTEGRITY_FAILURE')
    # C verifies a WORLD occurrence and its digest, not the plant's transition
    # law. The independent offline audit separately verifies the physics.
    w=self.db.execute("SELECT body,digest FROM event WHERE episode_id=? AND kind='WORLD'",(ep,)).fetchone()
    ensure(w is not None and json.loads(w['body'])==
           {'choice':e['choice'],'before':e['temperature'],'after':e['after_temp']} and
           w['digest']==sha({'id':self.db.execute("SELECT id FROM event WHERE episode_id=? AND kind='WORLD'",(ep,)).fetchone()[0],
                            'episode':ep,'kind':'WORLD','body':json.loads(w['body'])}),
           'WORLD_EVENT_CUSTODY_FAILURE')
    expected_logical,expected_pe=CNeuron.choose(e['temperature'],e['theta_read'])
    ensure(e['logical_choice']==expected_logical and
           e['choice']==map_action(expected_logical,e['sign_read']) and
           e['choice_PE_sha']==expected_pe,'C_OR_WORLD_INTEGRITY_FAILURE')
    ok=(trans==expected_b)
    reason=('VALID' if ok else 'MISSING' if trans is None else 'B_LINEAGE_OR_EFFECT_MISMATCH')
    current=self.state()
    proposed_theta,proposed_sign=propose_P(e['theta_read'],e['sign_read'],e['temperature'],
                                               e['logical_choice'],a)
    credit=0
    if e['learning'] and ok and (proposed_theta,proposed_sign)!=(e['theta_read'],e['sign_read']):
     if e['P_version_read']!=current['version']:reason='STALE_P_VERSION'
     elif self.policy()['mode']!='execute':
      return {'episode':ep,'kind':kind,'status':'BLOCKED','reason':'POLICY_VERIFY_DENIAL'}
     elif current['commits']>=self.policy()['ceiling']:
      return {'episode':ep,'kind':kind,'status':'BLOCKED','reason':'RESOURCE_EXHAUSTION'}
     else:
      self.db.execute('INSERT INTO p_intent VALUES(1,?,?,?,?,?,?)',
                      (ep,current['version'],current['theta'],proposed_theta,
                       current['actuator_sign'],proposed_sign))
      self.db.execute('UPDATE p SET theta=?,actuator_sign=?,version=version+1,commits=commits+1 WHERE singleton=1 AND version=? AND theta=? AND actuator_sign=?',
                      (proposed_theta,proposed_sign,current['version'],current['theta'],current['actuator_sign']))
      ensure(self.db.execute('SELECT changes()').fetchone()[0]==1,'P_CAS_REJECTED')
      self.db.execute('DELETE FROM p_intent WHERE singleton=1')
      event_id,d=self._log(ep,'P_GRANT',{'old_theta':current['theta'],'new_theta':proposed_theta,
                               'old_sign':current['actuator_sign'],'new_sign':proposed_sign,
                               'expected_version':current['version'],'source_A_digest':e['A_digest']})
      self.db.execute('INSERT INTO p_grant VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                      (ep,event_id,current['version'],current['version']+1,current['theta'],proposed_theta,
                       current['actuator_sign'],proposed_sign,e['A_digest'],self.policy()['revision'],d))
      credit=1;reason='P_COMMIT'
    self._log(ep,kind,{'accepted':ok,'reason':reason,'P_grant':credit,
                        'A_event_digest':e['A_digest']})
    self.db.execute('UPDATE episode SET credit=?,P_version_end=?,reason=?,stage=? WHERE id=?',
                    (credit,self.state()['version'],reason,'SETTLED',ep))
   else:raise ValueError('INVALID_PENDING_KIND')
   self.db.execute("UPDATE pending SET status='DONE' WHERE id=?",(q['id'],))
   return {'episode':ep,'kind':kind,'pending_id':q['id'],'stage':'SETTLED' if kind=='C_CREDIT' else 'RUNNING'}
  return self._tx(fn)
 def drain(self,*,limit=1000):
  steps=0
  while steps<limit:
   x=self.dispatch()
   if x is None or x.get('status')=='BLOCKED':break
   steps+=1
  else:raise ValueError('DISPATCH_LIMIT_REACHED')
  return steps
 def result(self,ep):
  e=self.db.execute('SELECT * FROM episode WHERE id=?',(ep,)).fetchone()
  ensure(e is not None and e['stage']=='SETTLED','EPISODE_NOT_SETTLED')
  return {'episode':ep,'before':e['temperature'],'after':e['after_temp'],'choice':e['choice'],
          'verdict':e['verdict'],'credit':e['credit'],'P_version_read':e['P_version_read'],
          'improved':abs(e['after_temp']-self.world.setpoint)<abs(e['temperature']-self.world.setpoint),
          'reason':e['reason']}
 def trial(self,temperature,*,learning=True,feedback='genuine'):
  eid=self.submit(temperature,learning=learning,feedback=feedback)
  self.drain();return self.result(eid)
 def audit(self):
  # Audit reconstructs every actor result from original PE computation.
  es=[dict(r) for r in self.db.execute('SELECT * FROM episode ORDER BY id')]
  events=[dict(r) for r in self.db.execute('SELECT * FROM event ORDER BY id')]
  pending=[dict(r) for r in self.db.execute('SELECT * FROM pending ORDER BY id')]
  grants=[dict(r) for r in self.db.execute('SELECT * FROM p_grant ORDER BY episode_id')]
  for k,x in enumerate(events):
   ensure(x['id']==k and x['digest']==sha({'id':k,'episode':x['episode_id'],
                 'kind':x['kind'],'body':json.loads(x['body'])}),'T17_EVENT_DIGEST_DRIFT')
  ensure(all(x['episode_id']<len(es) for x in events),'T17_EVENT_FOREIGN_EPISODE')
  ensure(self.db.execute('SELECT count(*) FROM p_intent').fetchone()[0]==0,'T17_UNCONSUMED_P_INTENT')
  for ep in es:
   ev=[x for x in events if x['episode_id']==ep['id']]
   kinds=[x['kind'] for x in ev]
   ensure(kinds==list(STAGES[:len([x for x in kinds if x!='P_GRANT'])]) or
          (kinds==['C_PE','WORLD','A_PE','B_RELAY','P_GRANT','C_CREDIT']),
          'T17_STAGE_EVENT_SEQUENCE')
   if 'C_PE' in kinds:
    c=json.loads(ev[0]['body'])
    logical,pe=CNeuron.choose(ep['temperature'],c['theta'])
    choice=map_action(logical,c['actuator_sign'])
    ensure(c=={'temperature':ep['temperature'],'choice':choice,'logical_choice':logical,
                'actuator_sign':c['actuator_sign'],'theta':c['theta'],
               'P_version':c['P_version'],'PE_digest':pe} and
           ep['P_version_read']==c['P_version'] and ep['theta_read']==c['theta'] and
           ep['sign_read']==c['actuator_sign'] and ep['logical_choice']==logical,
           'T17_C_PE_REPLAY_DRIFT')
   if 'WORLD' in kinds:
    w=json.loads(ev[1]['body'])
    ensure(w=={'before':ep['temperature'],'choice':ep['choice'],
                'after':self.world.apply(ep['temperature'],ep['choice'])} and
           ep['after_temp']==w['after'],'T17_WORLD_REPLAY_DRIFT')
   if 'A_PE' in kinds:
    a=judge_with_effect(ep['temperature'],ep['after_temp'],self.world.setpoint)
    ensure(json.loads(ev[2]['body'])==a and ep['A_json']==encode(a) and
           ep['A_digest']==ev[2]['digest'] and ep['verdict']==a['verdict'],
           'T17_A_PE_REPLAY_DRIFT')
   if 'B_RELAY' in kinds:
    expected=forward_with_effect(ep['id'],json.loads(ep['A_json']))
    actual=json.loads(ep['B_json']);logged=json.loads(ev[3]['body'])
    if ep['transport']=='missing':expected=None
    if ep['transport']=='wrong_lineage':expected=dict(expected,episode=ep['id']+1)
    if ep['transport']=='altered':expected=dict(expected,verdict='WORSENED' if expected['verdict']!='WORSENED' else 'IMPROVED')
    if ep['transport']=='effect_tamper':expected=dict(expected,effect_direction=(-expected['effect_direction'] if expected['effect_direction'] else 1))
    ensure(actual==logged==expected,'T17_B_RELAY_REPLAY_DRIFT')
   if ep['stage']=='SETTLED':
    ensure(kinds[-1]=='C_CREDIT' and ep['P_version_end'] is not None,'T17_C_FINAL_MISSING')
    if ep['credit']:
     matching=[g for g in grants if g['episode_id']==ep['id']]
     ensure(len(matching)==1 and 'P_GRANT' in kinds and
            matching[0]['A_event_digest']==ep['A_digest'] and
            matching[0]['grant_digest']==ev[-2]['digest'] and
            matching[0]['event_id']==ev[-2]['id'] and
            matching[0]['expected_version']==ep['P_version_read'] and
            matching[0]['new_version']==ep['P_version_read']+1 and
            matching[0]['old_theta']==ep['theta_read'] and matching[0]['old_sign']==ep['sign_read'] and
            (matching[0]['new_theta'],matching[0]['new_sign'])==propose_P(ep['theta_read'],ep['sign_read'],ep['temperature'],ep['logical_choice'],json.loads(ep['A_json'])),
            'T17_P_GRANT_CUSTODY_DRIFT')
    else:ensure('P_GRANT' not in kinds,'T17_UNGRANTED_P_EVENT')
  for e in pending:
   ep=es[e['episode_id']];idx=STAGES.index(e['kind'])
   completed=STAGES.index(ep['stage']) if ep['stage']!='SETTLED' else len(STAGES)
   ensure((e['status']=='DONE')==(idx<completed),'T17_PENDING_STATUS_DRIFT')
  state=self.state()
  ensure(len(grants)==state['commits']==state['version']==sum(e['credit'] for e in es),
         'T17_P_VERSION_COUNT_DRIFT')
  # Reconstruct committed P trajectory in chronological grant order.
  theta=int(dict(self.db.execute('SELECT key,value FROM config'))['initial_theta'])
  sign=0
  for version,g in enumerate(sorted(grants,key=lambda r:r['expected_version'])):
   ensure(g['expected_version']==version and g['old_theta']==theta and g['old_sign']==sign and
          g['new_version']==version+1,'T17_P_TRAJECTORY_DRIFT')
   theta=g['new_theta'];sign=g['new_sign']
  ensure(state['theta']==theta and state['actuator_sign']==sign,'T17_P_STATE_DRIFT')
  fence=self.db.execute("SELECT sql FROM sqlite_master WHERE name='p_update_guard'").fetchone()
  ensure(fence is not None and fence[0]==FENCE_SCHEMA,'T17_P_FENCE_DRIFT')
  return {'episodes':len(es),'settled':sum(e['stage']=='SETTLED' for e in es),
          'pending':sum(e['status']=='QUEUED' for e in pending),
          'events':len(events),'P_grants':len(grants),'P_theta':state['theta'],'P_sign':state['actuator_sign'],
          'P_version':state['version'],'dispatcher_slots':sum(e['status']=='DONE' for e in pending),
          'rows_sha256':sha(es),'events_sha256':sha(events),
          'original_SPK_native_BV':False,'original_SPK_native_learning':False}
