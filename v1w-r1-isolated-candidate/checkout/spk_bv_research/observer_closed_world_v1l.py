"""SPK BV v1l: laboratory two-port observer. NEVER native testimony.

A finite, in-process transition model makes delivered, lost, suppressed, pending,
and unobserved worlds distinguishable only when independent coverage is present.
It does NOT provide authenticity of external event traces or receiver judgment.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from spk_bv_research.off_on_v0t import require
from spk_bv_research.receiver_witness_boundary_v1k import SCHEMA as K_SCHEMA,STATUS as K_STATUS

SCHEMA='spk-bv-isolated-two-port-observer-proof-of-concept/v1l'
STATUS='LAB_CLOSED_WORLD_OBSERVER_NO_NATIVE_ABSENCE_AUTHORITY'
KINDS=('DELIVERED','SENDER_PORT_SILENCE','TRANSPORT_GAP','COVERAGE_LOSS',
       'PENDING','NO_EXPECTATION','LATE_ACK','MISMATCHED_INGRESS')

@dataclass(frozen=True, slots=True)
class Episode:
    name:str
    expectation_before_decision:bool=True
    receiver_ack_before_decision:bool=True
    until_tick:int=12
    deadline_tick:int=10
    sender_tap_covered:bool=True
    receiver_tap_covered:bool=True
    control_coverage_independent:bool=True
    sender_emit:bool=False
    receiver_ingress:bool=False
    sender_event_id:str='lab.future.event.1'
    receiver_event_id:str='lab.future.event.1'


def validate_ep(e:Episode):
    require(type(e) is Episode,'only in-process typed experiment scenarios allowed')
    require(type(e.name) is str and 1<=len(e.name)<=60 and
            all(c.isascii() and (c.isalnum() or c in '_-') for c in e.name),
            'bad lab scenario name')
    for field in ('expectation_before_decision','receiver_ack_before_decision',
      'sender_tap_covered','receiver_tap_covered','control_coverage_independent',
      'sender_emit','receiver_ingress'):
        require(type(getattr(e,field)) is bool,'invalid lab boolean '+field)
    for field in ('until_tick','deadline_tick'):
        val=getattr(e,field)
        require(type(val) is int and 0<=val<=100000,'invalid lab tick '+field)
    require(e.deadline_tick>=4,'expectation/decision time must precede deadline')
    for field in ('sender_event_id','receiver_event_id'):
        val=getattr(e,field)
        require(type(val) is str and 1<=len(val)<=96 and
                all(c.isascii() and (c.isalnum() or c in '_.:-') for c in val),
                'invalid lab event id')
    return e


def run_lab(e:Episode):
    """Observer's evidence, NOT hidden ground truth or imported witness dict."""
    validate_ep(e)
    coverage=(e.sender_tap_covered and e.receiver_tap_covered and
              e.control_coverage_independent)
    if not e.expectation_before_decision: classification='NO_EXPECTATION'
    elif not e.receiver_ack_before_decision: classification='LATE_ACK'
    elif e.until_tick<e.deadline_tick: classification='PENDING'
    elif not coverage: classification='COVERAGE_LOSS'
    elif e.receiver_ingress and (not e.sender_emit or e.receiver_event_id!=e.sender_event_id):
        classification='MISMATCHED_INGRESS'
    elif e.sender_emit and e.receiver_ingress: classification='DELIVERED'
    elif e.sender_emit and not e.receiver_ingress: classification='TRANSPORT_GAP'
    else: classification='SENDER_PORT_SILENCE'
    # Incomplete coverage never permits concluding absence, even if the model's
    # hidden sender_emit=False is known by experimenter.
    result={
      'lab_scenario':e.name,
      'classification':classification,
      'predecision_commit_observed_in_lab':e.expectation_before_decision,
      'predecision_ack_observed_in_lab':e.receiver_ack_before_decision,
      'complete_independent_two_port_coverage_in_lab':coverage and e.until_tick>=e.deadline_tick,
      'expected_event_id':e.sender_event_id,
      'sender_tap_saw_event':e.sender_emit if coverage and e.until_tick>=e.deadline_tick else None,
      'receiver_tap_saw_event':e.receiver_ingress if coverage and e.until_tick>=e.deadline_tick else None,
      'missing_from_receiver_in_lab':(e.sender_emit and not e.receiver_ingress)
         if coverage and e.until_tick>=e.deadline_tick else None,
      'sender_decision_cause_known_to_receiver':False,
      'endogenous_value_judgment':False,
      'native_absence_witness':False,
    }
    return result


def experiment_cases():
    return (
      Episode('observed_delivery',sender_emit=True,receiver_ingress=True),
      Episode('sender_port_silence'),
      Episode('transport_gap',sender_emit=True),
      Episode('receiver_coverage_lost',receiver_tap_covered=False),
      Episode('sender_coverage_lost',sender_tap_covered=False,sender_emit=True),
      Episode('control_channel_lost',control_coverage_independent=False),
      Episode('pending',until_tick=9),
      Episode('no_precommit',expectation_before_decision=False),
      Episode('late_ack',receiver_ack_before_decision=False),
      Episode('wrong_ingress_identity',sender_emit=True,receiver_ingress=True,
              receiver_event_id='lab.unrelated'),
    )


def audit(k,kbytes,*,jbytes,ibytes,hbytes,gbytes,demo=False):
    require(type(k) is dict and type(kbytes) is bytes and kbytes and
            json.loads(kbytes)==k,'v1k reference mismatch')
    require(k.get('schema')==K_SCHEMA and k.get('status')==K_STATUS and
      k.get('native_v1j_recomputation_verified_in_this_run') is True and
      k.get('native_absence_witnesses')==0 and
      k.get('endogenous_receiver_judgments')==0 and
      k.get('native_updates_applied')==0 and
      k.get('causal_credit_or_learning_proven') is False and
      k.get('shadow_scenarios_native_attested')==0 and
      k.get('witness_authority_barrier')=='UNTRUSTED_JSON_CANNOT_CERTIFY_NATIVE_EVENT_ABSENCE' and
      k.get('receiver_local_direct_scope')=={
        'B':{'source':'A','direct':True,'missing_witnesses':True},
        'C':{'source':'B','direct_from_A':False,'missing_witnesses':True}} and
      type(k.get('shadow_plan_supplied')) is bool and
      type(k.get('shadow_scenarios')) is list and
      (bool(k.get('shadow_scenarios'))==k['shadow_plan_supplied']),
      'v1k unsupported authority promotion')
    require(all(type(b) is bytes and b for b in (jbytes,ibytes,hbytes,gbytes)),
            'reference bytes missing')
    for version,b in [('v1j',jbytes),('v1i',ibytes),('v1h',hbytes),('v1g1',gbytes)]:
        require(k.get('reference_'+version+'_sha256')==sha256(b).hexdigest(),
                'v1k predecessor hash mismatch '+version)
    require(type(demo) is bool,'demo must be bool')
    rows=[run_lab(e) for e in experiment_cases()] if demo else []
    require(len({r['lab_scenario'] for r in rows})==len(rows),'duplicate scenario name')
    return {
      'schema':SCHEMA,'status':STATUS,
      'source_kind':'IN_PROCESS_FINITE_LAB_SIMULATION_NOT_NATIVE_SPK',
      'reference_v1k_sha256':sha256(kbytes).hexdigest(),
      **{'reference_'+ver+'_sha256':sha256(b).hexdigest()
         for ver,b in [('v1j',jbytes),('v1i',ibytes),('v1h',hbytes),('v1g1',gbytes)]},
      'native_v1k_recomputation_verified_in_this_run':False,
      'native_absence_witnesses':0,'native_scored_receiver_judgments':0,
      'native_updates_applied':0,'learning_or_causal_utility_identified':False,
      'demo_lab_requested':demo,'lab_cases':rows,'lab_cases_native_attested':0,
      'two_port_observer_finding':
        'WITH_CLOSED_WORLD_INDEPENDENT_COVERAGE_CAN_SEPARATE_PORT_SILENCE_FROM_TRANSPORT_GAP',
      'knowledge_boundary':
        'NO_SENDER_DECISION_CAUSE_WITHOUT_INDEPENDENT_DECISION_RECORD',
      'claims_excluded':[
        'lab-controlled-port-coverage-is-not-a-native-coverage-certificate',
        'sandbox-precommit-and-ack-are-not-native-receiver-messages',
        'in-process-test-execution-does-not-authenticate-uploaded-event-records',
        'a-sender-port-silence-does-not-prove-the-senders-internal-choice',
        'receiver-ingress-only-projection-remains-ambiguous',
        'control-channel-failure-must-not-be-interpreted-as-missing-event',
        'no-B-to-C-ancestral-authority-from-an-A-to-B-two-port-watch',
        'no-endogenous-scored-judgment-or-operator-commit-or-learning',
        'not-a-certified-algebra-rewrite-or-hardware-architecture-promotion'
      ]
    }
