"""C -> B -> A -> B -> C executable counterfactual learning research.

All PE computations run the ORIGINAL pinned _compute_local (no copy).  The
network, A goal, message protocol and bounded policy overlay are separately
implemented in this additive Python fork. This is NOT the frozen BV runtime,
trusted A sensing, secure C identity or native SPK self-learning.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from spk_architecture_v1.pe_execution_v1b import _compute_local

class LoopBoundary(ValueError): pass

def require(condition, code):
    if not condition: raise LoopBoundary(code)

def compact(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def digest(value):
    return sha256(compact(value)).hexdigest()

@dataclass(frozen=True)
class Node:
    node_id: str
    instructions: tuple
    state_bits: int = 16
    fractional_bits: int = 0

# All computations use the existing PE instruction semantics.  No new opcode.
def pe(node_name, instructions, tick, channels):
    require(type(tick) is int and 0<=tick<10000, 'INVALID_TICK')
    require(type(channels) is tuple and all(type(c) is int and c>=0 for c in channels), 'INVALID_CHANNELS')
    n=Node(node_name, tuple(instructions))
    raw, guard, emitted=_compute_local(n, [0,0], tick, channels)
    require(type(raw) is int and type(guard) is bool and type(emitted) is tuple,'PE_SHAPE')
    return {'raw':raw,'guard':guard,'emissions':emitted,'pe_node':node_name,'tick':tick}

def emit_single(name, incoming, input_ch, output_ch, tick):
    require(incoming==input_ch,'WRONG_INPUT_CHANNEL')
    result=pe(name,(('ACC',(1,input_ch)),('CMP',1),('EMIT',output_ch),('RESET',0)),tick,(incoming,))
    require(result['emissions']==(output_ch,), 'MISSING_PE_EMISSION')
    return result

GOALS={0:5,1:11}
INITIAL={0:12,1:11}  # deliberately adverse starting policy

class CPolicy:
    """Per-neuron bounded policy overlay with explicit pending custody.

    Its two parameters select between two valid instruction programs. This
    is not a modification of the frozen PE's Sigma, sigma or memory contracts.
    """
    def __init__(self, learn):
        require(type(learn) is bool,'LEARNING_SWITCH_DOMAIN')
        self.learn=learn
        self.table=dict(INITIAL)
        self.versions={0:0,1:0}
        self.next_decision=0
        self.pending={}
        self.consumed=set()
        self.accepted=0
        self.updates=0
        self.rejects=[]

    def choose(self, cue):
        require(type(cue) is int and cue in GOALS,'UNKNOWN_CUE')
        did=self.next_decision;self.next_decision+=1
        channel=self.table[cue]
        c=emit_single('C',0,0,channel,0)
        decision={'decision_id':did,'cue':cue,'choice':channel,
                  'policy_version':self.versions[cue],
                  'pe_raw':c['raw'],'pe_emissions':list(c['emissions']),
                  'decision_sha256':digest({'decision_id':did,'cue':cue,'choice':channel,'policy_version':self.versions[cue]})}
        self.pending[did]=decision
        return decision,c

    def apply(self, relay, current_tick=4):
        require(type(current_tick) is int and current_tick>=4,'BAD_RETURN_TICK')
        require(type(relay) is dict and set(relay)=={'payload','a_sha256','b_sha256','b_channel','c_channel'},'RELAY_SCHEMA')
        p=relay['payload']
        require(type(p) is dict and set(p)=={'decision_id','cue','decision_sha256','observed_raw','goal_raw','outcome','a_feedback_ch'},'A_PAYLOAD_SCHEMA')
        did=p['decision_id']
        require(type(did) is int and did not in self.consumed,'REPLAYED_FEEDBACK')
        require(did in self.pending,'NO_PENDING_DECISION')
        dec=self.pending[did]
        require(p['cue']==dec['cue'] and p['decision_sha256']==dec['decision_sha256'],'DECISION_BINDING_MISMATCH')
        require(dec['policy_version']==self.versions[dec['cue']],'STALE_POLICY_VERSION')
        require(type(p['observed_raw']) is int and 0<=p['observed_raw']<65536,'MEASUREMENT_DOMAIN')
        require(type(p['goal_raw']) is int and p['goal_raw'] in (5,11),'GOAL_DOMAIN')
        require(p['outcome'] in ('IMPROVED','WORSENED','UNCHANGED'),'OUTCOME_DOMAIN')
        ch={'IMPROVED':41,'WORSENED':42,'UNCHANGED':43}[p['outcome']]
        require(p['a_feedback_ch']==ch,'A_CH_OUTCOME_CONFLICT')
        require(relay['a_sha256']==digest(p),'A_DIGEST_MISMATCH')
        require(relay['b_sha256']==digest({'a_sha256':relay['a_sha256'],'b_channel':relay['b_channel'],'c_channel':relay['c_channel']}),'B_DIGEST_MISMATCH')
        require(relay['b_channel']==ch+10 and relay['c_channel']==ch+20,'INVERSE_PATH_MISMATCH')
        require(current_tick<=7,'FEEDBACK_EXPIRED')
        # An actual PE call at C for the reverse-path arrival.
        c_feedback=emit_single('C-return',ch+20,ch+20,ch+30,current_tick)
        self.consumed.add(did);del self.pending[did]
        self.accepted+=1
        updated=False
        if self.learn and p['outcome']=='WORSENED':
            # This learning rule is local to C's experimental policy overlay.
            cue=dec['cue'];self.table[cue]=11 if self.table[cue]==12 else 12
            self.versions[cue]+=1
            self.updates+=1;updated=True
        return {'decision_id':did,'feedback':p['outcome'],'policy_updated':updated,
                'C_return_emission':list(c_feedback['emissions']),
                'C_policy_after':dict(self.table)}

def a_measure(cue, b_emission, decision, *, allow_absent=False):
    require(cue in GOALS,'UNKNOWN_A_GOAL')
    if b_emission is None:
        require(allow_absent,'ABSENT_FORWARD_UNAUTHORIZED')
        a=pe('A',(('ACC',(5,3)),('ACC',(11,4))),2,())
        outcome='UNCHANGED';raw=a['raw']
    else:
        require(b_emission in (31,32),'BAD_B_EMISSION')
        channel=3 if b_emission==31 else 4
        a=pe('A',(('ACC',(5,3)),('ACC',(11,4))),2,(channel,))
        raw=a['raw'];outcome='IMPROVED' if raw==GOALS[cue] else 'WORSENED'
    return {'decision_id':decision['decision_id'],'cue':cue,
            'decision_sha256':decision['decision_sha256'],'observed_raw':raw,
            'goal_raw':GOALS[cue],'outcome':outcome,
            'a_feedback_ch':{'IMPROVED':41,'WORSENED':42,'UNCHANGED':43}[outcome]},a

def forward(decision):
    c_channel=decision['choice'];require(c_channel in (11,12),'C_BAD_ACTION')
    b=emit_single('B-forward',1 if c_channel==11 else 2,
                  1 if c_channel==11 else 2,31 if c_channel==11 else 32,1)
    return b

def backward(a_packet):
    ch=a_packet['a_feedback_ch']
    a=emit_single('A-return',50,50,ch,3)
    b=emit_single('B-return',ch,ch,ch+10,4)
    # C emission is performed only in CPolicy.apply().
    return {'payload':a_packet,'a_sha256':digest(a_packet),
            'b_channel':b['emissions'][0], 'c_channel':b['emissions'][0]+10,
            'b_sha256':digest({'a_sha256':digest(a_packet),
                               'b_channel':b['emissions'][0],
                               'c_channel':b['emissions'][0]+10})},a,b

def episode(policy,cue,feedback=True):
    decision,c=policy.choose(cue)
    b=forward(decision)
    packet,a=a_measure(cue,b['emissions'][0],decision)
    require(a['raw']==packet['observed_raw'],'A_MEASUREMENT_DID_NOT_COME_FROM_PE')
    delivered=None
    if feedback:
        relay,a_out,b_ret=backward(packet)
        delivered=policy.apply(relay)
    return {'id':decision['decision_id'],'cue':cue,'C_choice':decision['choice'],
            'C_emit':list(c['emissions']),'B_emit':list(b['emissions']),
            'A_raw':a['raw'],'A_goal':packet['goal_raw'],'A_outcome':packet['outcome'],
            'feedback_returned':delivered is not None,
            'updated':bool(delivered and delivered['policy_updated']),
            'C_policy_after':dict(policy.table)}

def compare_interventions(cue,decision):
    """Intervene on C's emitted channel and recompute the *real PE* B and A.

    Only an identified causal effect INSIDE this deterministic host-authored
    fork; no intervention on native C or independently sensed A outcome.
    """
    actual=forward(decision)
    p_actual,_=a_measure(cue,actual['emissions'][0],decision)
    opposite=dict(decision);opposite['choice']=12 if decision['choice']==11 else 11
    control=forward(opposite)
    p_opposite,_=a_measure(cue,control['emissions'][0],decision)
    absent,_=a_measure(cue,None,decision,allow_absent=True)
    return {'actual_success':int(p_actual['outcome']=='IMPROVED'),
            'opposite_success':int(p_opposite['outcome']=='IMPROVED'),
            'absent_outcome':absent['outcome'],'absent_raw':absent['observed_raw'],
            'outcome_delta':int(p_actual['outcome']=='IMPROVED')-int(p_opposite['outcome']=='IMPROVED')}

def trial(learn, sequence):
    policy=CPolicy(learn)
    records=[];interventions=[]
    for cue in sequence:
        # Construct a controlled counterfactual before any policy update.
        dec,c=policy.choose(cue)
        cf=compare_interventions(cue,dec)
        b=forward(dec)
        packet,a=a_measure(cue,b['emissions'][0],dec)
        require(a['raw']==packet['observed_raw'],'PE_A_REPLAY_DRIFT')
        relay,af,bf=backward(packet)
        if learn:
            received=policy.apply(relay)
        else:
            # Control runs the same round trip, but adaptive policy is disabled.
            received=policy.apply(relay)
        records.append({'case':dec['decision_id'],'cue':cue,'C_action':dec['choice'],
                        'A_raw':a['raw'],'A_goal':GOALS[cue],
                        'A_outcome':packet['outcome'],'C_policy_after':dict(policy.table),
                        'C_updated':received['policy_updated'],'C_feedback_emission':received['C_return_emission']})
        interventions.append(cf)
    require(policy.next_decision==len(sequence) and policy.accepted==len(sequence) and not policy.pending,'UNFINISHED_LOOP')
    return {'learn':learn,'episodes':len(records),'successes':sum(x['A_outcome']=='IMPROVED' for x in records),
            'failures':sum(x['A_outcome']=='WORSENED' for x in records),
            'updates':policy.updates,'emitted':policy.accepted,
            'final_policy':dict(policy.table),'records':records,'interventions':interventions}
