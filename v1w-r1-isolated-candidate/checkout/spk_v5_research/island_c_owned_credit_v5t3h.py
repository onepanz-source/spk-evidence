"""T3h: research-only A1b C-authored verdict with forward decision marker, C sensor,
closure and routed C->B->A consumption. Distinguishes computation from learning.
No external photo labels or oracle reward are provided to this 3-neuron case.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
from hashlib import sha256
import json
from datetime import datetime
from collections import Counter

from search.spk_24n_independent_oracle_v0 import CaseV0,NodeV0,EdgeV0,EventV0
from spk_architecture_v1.pe_execution_v1b import execute_on_pes_v1b
from spk_architecture_v1.pe_fabric_v1a import plan_v1a
from spk_v5_research.island_objective_v5t1 import OVEREMIT,SILENT
from spk_v5_research.island_successor_competition_v5t3e import PERSIST
from spk_v5_research.island_real_transition_v5t3d import ALLOWED_GAPS_SECONDS

SCHEMA='spk-v5-t3h-c-authored-reverse-credit/research-v0'
CO2_THRESHOLD=600.0
LIGHT_THRESHOLD=200.0
ARMS=('current','persist','silent')
# Channel assignments are deliberately disjoint from A's chosen light program.
A_CREDIT=(('ACC',(32,5)),('CMP',32),('EMIT',20),('RESET',0),
          ('ACC',(4,3)),('CMP',4),('EMIT',13),('RESET',0),
          ('ACC',(4,4)),('CMP',4),('EMIT',14),('RESET',0))
B_PROGRAM=(('ACC',(1,0)),('CMP',1),('EMIT',7),('RESET',0),
           ('ACC',(1,5)),('CMP',1),('EMIT',20),('RESET',0),
           ('ACC',(1,3)),('CMP',1),('EMIT',13),('RESET',0),
           ('ACC',(1,4)),('CMP',1),('EMIT',14),('RESET',0))
# A valid C verdict requires independent sensor presence (16/17),
# decision marker custody (32), and closure (64). A forwarded spike adds 2.
# Sum 112 or 115: agreement; 113 or 114: disagreement. A1b computes
# these *inside C* via descending threshold guards and conditional reset.
C_PROGRAM=(('ACC',(16,5)),('ACC',(17,4)),('ACC',(2,2)),
           ('ACC',(32,3)),('ACC',(64,6)),
           ('CMP',64),('EMIT',9),
           ('CMP',115),('EMIT',11),('RESET',0),
           ('CMP',114),('EMIT',12),('RESET',0),
           ('CMP',113),('EMIT',12),('RESET',0),
           ('CMP',112),('EMIT',11),('RESET',0))
EDGES=(('A',7,'B',0),('A',20,'B',5),('B',7,'C',2),('B',20,'C',3),
       ('C',11,'B',3),('C',12,'B',4),('B',13,'A',3),('B',14,'A',4))

class CreditAdmissionError(ValueError):pass

@dataclass(frozen=True)
class Measurement:
    previous_stamp:str
    current_stamp:str
    previous_light:float
    current_light:float
    co2_current:float|None
    # "sensor_visible" says whether C receives its separate binary threshold adapter.
    sensor_visible:bool=True
    send_decision:bool=True
    reverse_enabled:bool=True
    forward_enabled:bool=True


def validate(m:Measurement,arm:str):
    if type(m) is not Measurement or arm not in ARMS or any(type(v) is not bool for v in
      (m.sensor_visible,m.send_decision,m.reverse_enabled,m.forward_enabled)):
        raise CreditAdmissionError('invalid candidate or typed measurement')
    try:
        delta=(datetime.strptime(m.current_stamp,'%Y-%m-%d %H:%M:%S')-
               datetime.strptime(m.previous_stamp,'%Y-%m-%d %H:%M:%S')).total_seconds()
    except (ValueError,TypeError) as e:
        raise CreditAdmissionError('invalid physical timestamp') from e
    if delta not in ALLOWED_GAPS_SECONDS:
        raise CreditAdmissionError('physical readings must be consecutive')
    from math import isfinite
    for value in (m.previous_light,m.current_light,m.co2_current):
        if value is not None and (type(value) not in (float,int) or not isfinite(value) or value<0):
            raise CreditAdmissionError('invalid sensor value')
    if m.co2_current is None and m.sensor_visible:
        raise CreditAdmissionError('cannot invent independent C evidence')
    if type(m.previous_light) not in (float,int) or type(m.current_light) not in (float,int):
        raise CreditAdmissionError('light sensor required')


def build_case(m:Measurement,arm:str)->CaseV0:
    validate(m,arm)
    program={'current':OVEREMIT,'persist':PERSIST,'silent':SILENT}[arm]
    nodes=(NodeV0('A',8,0,0,program+A_CREDIT),
           NodeV0('B',8,0,0,B_PROGRAM),NodeV0('C',8,0,0,C_PROGRAM))
    edges=tuple(EdgeV0(*row,1) for row in EDGES if
                (m.reverse_enabled or row[0]!='C' and not(row[0]=='B' and row[2]=='A'))
                and (m.forward_enabled or row not in (('A',7,'B',0),('B',7,'C',2))))
    events=[EventV0(10,'A',1 if m.previous_light>=LIGHT_THRESHOLD else 0)]
    if m.current_light>=LIGHT_THRESHOLD:events.append(EventV0(11,'A',2))
    if m.send_decision:events.append(EventV0(12,'A',5))
    if m.sensor_visible:events.append(EventV0(12,'C',4 if m.co2_current>=CO2_THRESHOLD else 5))
    events.append(EventV0(15,'C',6))
    return CaseV0(nodes,edges,tuple(events))


def execute(m:Measurement,arm:str)->dict:
    """One native A1b *execution*, not native learning or signed neuron identity."""
    case=build_case(m,arm)
    result=execute_on_pes_v1b(case,plan_v1a(case,'spread'))['result']
    emissions=result['emissions']
    at=lambda node,channel:[e for e in emissions if e['node_id']==node and e['channel']==channel]
    obs=result['observations']['batches']
    # Event count and route checks protect against interpreting missing transport
    # as legitimate silence. A1b transport is ideal; explicit drops simulate failure.
    a_forward=at('A',7);b_forward=at('B',7)
    c_forward=[b for b in obs if b['node_id']=='C' and 2 in b['channels']]
    if len(a_forward)>1 or len(b_forward)>1 or len(c_forward)>1:
        raise CreditAdmissionError('forward multiplicity invalid')
    forward_integrity=(len(a_forward)==len(b_forward)==len(c_forward) and
       all(x['timestamp']==11 for x in a_forward) and
       all(x['timestamp']==12 for x in b_forward) and
       all(x['timestamp']==13 for x in c_forward))
    # Decision marker must be physically observed at C to authorize ANY verdict.
    marker=len(at('A',20))==len(at('B',20))==1 and any(
      b['node_id']=='C' and b['timestamp']==14 and 3 in b['channels'] for b in obs)
    c_positive=at('C',11);c_negative=at('C',12)
    a_positive=at('A',13);a_negative=at('A',14)
    if len(c_positive)+len(c_negative)>1 or len(a_positive)+len(a_negative)>1:
        raise CreditAdmissionError('duplicate credit')
    if len(at('C',9))!=1 or at('C',9)[0]['timestamp']!=15:
        raise CreditAdmissionError('C closure not computed')
    source_c=(1 if c_positive else -1 if c_negative else None)
    consumed=(1 if a_positive else -1 if a_negative else None)
    if any(x['timestamp']!=15 for x in c_positive+c_negative) or any(
      x['timestamp']!=17 for x in a_positive+a_negative):
        raise CreditAdmissionError('incorrect credit timing')
    if not forward_integrity:
        status='forward_custody_failed';delivered=None
    elif not marker:
        status='decision_custody_failed';delivered=None
    elif not m.sensor_visible:
        status='C_evidence_missing';delivered=None
    elif source_c is None:
        raise CreditAdmissionError('C failed to compute verifiable local verdict')
    elif not m.reverse_enabled:
        status='reverse_delivery_lost';delivered=None
    elif consumed!=source_c:
        raise CreditAdmissionError('A did not consume C-computed credit')
    else:
        status='C_authored_credit_delivered';delivered=consumed
    if status=='C_authored_credit_delivered':
        assert source_c == (1 if (len(a_forward)>0)==(m.co2_current>=CO2_THRESHOLD) else -1)
    return {'schema':SCHEMA,'arm':arm,'status':status,
       'research_measurement_commit_sha256':sha256(json.dumps(asdict(m),sort_keys=True,separators=(',',':')).encode()).hexdigest(),
       'A_light_decision':bool(a_forward),'C_sensor_observed':m.sensor_visible,
       'C_decision_marker_received':marker,'C_computed_verdict':source_c,
       'A_consumed_credit':delivered,
       'A1b_emission_proof':[(x['timestamp'],x['node_id'],x['channel']) for x in emissions],
       'A1b_batch_count':len(obs),'source_authority':'A1b_derived_research_C_instructions',
       'external_photo_labels_seen':False,'native_BV_credit':False,'native_learning':False}


def compact_audit():
    cases=[];counter=Counter()
    for before in (False,True):
      for current in (False,True):
       for c_positive in (False,True,None):
        for arm in ARMS:
         for kind,extra in [('normal',{}),('reverse_loss',{'reverse_enabled':False}),
                            ('missing_marker',{'send_decision':False}),
                            ('forward_loss',{'forward_enabled':False})]:
          m=Measurement('2026-10-22 12:00:00','2026-10-22 12:01:00',
             300 if before else 5,300 if current else 5,
             None if c_positive is None else 800 if c_positive else 450,
             sensor_visible=c_positive is not None,**extra)
          r=execute(m,arm);counter[r['status']]+=1
          cases.append({'pattern':f'{int(before)}{int(current)}','C_sensor':c_positive,
              'arm':arm,'route':kind,'status':r['status'],'C_verdict':r['C_computed_verdict'],
              'A_credit':r['A_consumed_credit']})
    return {'schema':SCHEMA,'status':'C_OWNED_A1B_REVERSE_CREDIT_RESEARCH_PASS',
      'case_count':len(cases),'statuses':dict(sorted(counter.items())),'cases':cases,
      'claims_excluded':['no independent physical C sensor custody',
         'threshold adapter computes CO2 bin at host boundary',
         'no opaque signed native C identity, no native BV credit',
         'no native policy update or reinforcement learning',
         'synthetic truth-table, not new unseen external evaluation',
         'sender/reverse route omission in research A1b case is not real packet loss']}


def verify_custody(m:Measurement,arm:str,claim:dict):
    """Independently replay the three-neuron case; no report-controlled shortcuts."""
    if type(claim) is not dict or claim!=execute(m,arm):
        raise CreditAdmissionError('forged or noncanonical C-owned credit')
    return True
