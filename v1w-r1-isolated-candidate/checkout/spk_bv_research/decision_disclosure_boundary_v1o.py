"""SPK BV v1o: source-bound, non-native lower bound for decision disclosures.

This pure model NEVER authenticates a sender or delivers messages to a native
neuron. It tests whether a separately labelled laboratory decision record
could distinguish two otherwise T3-equivalent hypothetical worlds. A record
about a choice cannot, by itself, establish the cause of an absent event.
"""
from __future__ import annotations
from hashlib import sha256
import json
from spk_bv_research.off_on_v0t import require
from spk_bv_research.receiver_knowledge_disclosure_v1n import (
    SCHEMA as N_SCHEMA, STATUS as N_STATUS, TIERS as N_TIERS, _project,
)

SCHEMA='spk-bv-shadow-decision-disclosure-lower-bound/v1o'
STATUS='SOURCE_BOUND_T4_SHADOW_DECISION_VISIBILITY_NO_NATIVE_AUTHORITY'
EDGE='A->B:7->0'
LAB_EPISODE='shadow.future.episode'
EXPECTED_ID='shadow.future.event.1'
DECISION_ID='shadow.A.decision.1'
WORLD_IDS=('SHADOW_INTERNAL_CAUSE_A','SHADOW_INTERNAL_CAUSE_B')
EXCLUDED=[
 't4-laboratory-decision-records-not-native-neuron-or-scheduler-events',
 'lab-source-authentication-assumed-not-cryptographically-or-natively-proven',
 'native-receiver-B-does-not-receive-this-disclosure',
 'native-receiver-C-is-not-a-direct-recipient-of-A',
 'sha256-content-integrity-not-sender-authentication',
 'a-recorded-decision-is-not-proof-that-it-caused-an-absent-spike',
 'no-endogenous-objective-or-receiver-scored-judgment',
 'no-native-absence-certificate-no-committed-update-no-learning',
 'shadow-T4-not-certified-algebra-rewrite-or-frozen-architecture-promotion',
]


def canon(doc):
    return (json.dumps(doc,sort_keys=True,indent=2,ensure_ascii=True,allow_nan=False)+'\n').encode('utf-8')


def _strict_report(n, nbytes, m, mbytes):
    require(type(n) is dict and type(m) is dict and type(nbytes) is bytes and
            type(mbytes) is bytes and nbytes==canon(n) and mbytes==canon(m),
            'noncanonical source-bound inputs')
    require(n.get('schema')==N_SCHEMA and n.get('status')==N_STATUS and
            n.get('reference_v1m_sha256')==sha256(mbytes).hexdigest() and
            n.get('native_v1m_recomputation_verified_in_this_run') is True and
            m.get('schema')=='spk-bv-native-passive-two-port-trace-projection/v1m' and
            m.get('status')=='NATIVE_POSTHOC_ENDPOINT_TRACES_NOT_INDEPENDENT_OBSERVER' and
            m.get('full_native_scheduler_runs_recomputed_in_this_run')==4 and
            n.get('native_traces_in_v1m')==4,
            'source-bound v1n/v1m custody mismatch')
    for key,value in (
        ('attested_direct_A_to_B',True),('attested_direct_A_to_C',False),
        ('native_disclosure_channel_to_receiver_present',False),
        ('native_full_two_port_observer_present',False),
        ('native_receiver_can_identify_missing_sender_decision',False),
        ('shadow_internal_cause_ambiguous_even_through_T3',True),
        ('native_learning_proven',False),
    ):
        require(type(n.get(key)) is type(value) and n[key]==value,
                'authority/cause promotion '+key)
    for field in ('native_absence_witnesses','native_scored_receiver_judgments',
                  'native_operator_updates'):
        require(type(n.get(field)) is int and n[field]==0,'invalid native count '+field)
    require(n.get('native_fixture_sha256')==m.get('native_fixture_sha256') and
            n.get('frozen_native_sources')==m.get('frozen_native_sources') and
            n.get('native_original_edge_A_B')=={'sender_emissions':2,'receiver_ingress':2} and
            n.get('native_variant_edge_A_B')=={'sender_emissions':0,'receiver_ingress':0},
            'native edge identity mismatch')
    worlds=n.get('shadow_worlds')
    require(type(worlds) is list and len(worlds)==8 and
            all(type(w) is dict and type(w.get('world_id')) is str for w in worlds) and
            len(set(w['world_id'] for w in worlds))==8,
            'invalid finite-world inventory')
    byid={w['world_id']:w for w in worlds}
    require(set(WORLD_IDS).issubset(byid),'shadow cause examples unavailable')
    a,b=(byid[k] for k in WORLD_IDS)
    expected_fields=('ingress_count','sender_port_count','expected','covered')
    require(tuple(N_TIERS[-1][1])==expected_fields and
            _project(a,expected_fields)==_project(b,expected_fields)==(0,0,True,True) and
            a.get('world_origin')==b.get('world_origin')=='HYPOTHETICAL_NOT_EXECUTED' and
            a.get('hidden_decision_cause')=='OPERATOR_CAUSE_ASSUMED' and
            b.get('hidden_decision_cause')=='EXTERNAL_CAUSE_ASSUMED',
            'T3 cause indistinguishability changed')
    require(n.get('shadow_tier_authority')=='COUNTERFACTUAL_DISCLOSURE_MODEL_ONLY' and
            len(n.get('shadow_projection_tiers',[]))==4 and
            any(x=={'world_left':WORLD_IDS[0],'world_right':WORLD_IDS[1],
                    'first_distinguishable_at':'NOT_DISTINGUISHABLE_THROUGH_T3'}
                for x in n.get('shadow_distinguishability_tests',[])),
            'T3 model provenance changed')
    return a,b


def example_record(action: str) -> dict:
    """Only a proposed JSON payload, not a certificate or delivered message."""
    require(action in ('OPERATOR_VARIANT_SELECTED','NO_VARIANT_SELECTED'),
            'unsupported hypothetical action')
    return {
        'schema':'shadow.decision-record/v1o',
        'decision_id':DECISION_ID,'episode_id':LAB_EPISODE,
        'expected_event_id':EXPECTED_ID,'sender':'A','receiver':'B',
        'source_channel':7,'receiver_channel':0,
        'decision_tick':2,'ack_tick':1,'receipt_tick':3,'verdict_tick':4,
        'action':action,
        'authority':'UNTRUSTED_JSON_NOT_NATIVE',
    }


def inspect(record, *, declared_lab_producer=False, independent_receipt=False,
            covered=False, expected=False, direct_edge=True):
    """Fail-closed SHADOW classification; booleans are assumptions, not proofs.

    No output from this routine grants native authority. A locally asserted
    truthy flag cannot authenticate a producer or clock in the real fabric.
    """
    if record is None:
        return 'NO_DECISION_RECORD'
    if type(record) is not dict or set(record)!=set(example_record('OPERATOR_VARIANT_SELECTED')):
        return 'MALFORMED_RECORD'
    if (record.get('schema')!='shadow.decision-record/v1o' or
            record.get('authority')!='UNTRUSTED_JSON_NOT_NATIVE'):
        return 'MALFORMED_RECORD'
    if any(type(record.get(k)) is not str or not record[k]
           for k in ('decision_id','episode_id','expected_event_id',
                     'sender','receiver','action')):
        return 'MALFORMED_RECORD'
    if record['action'] not in ('OPERATOR_VARIANT_SELECTED','NO_VARIANT_SELECTED'):
        return 'MALFORMED_RECORD'
    if (record['sender']!='A' or record['receiver']!='B' or
            record['source_channel']!=7 or record['receiver_channel']!=0 or
            type(record['source_channel']) is not int or
            type(record['receiver_channel']) is not int or not direct_edge):
        return 'WRONG_DIRECT_EDGE'
    if (record['episode_id']!=LAB_EPISODE or record['decision_id']!=DECISION_ID or
            record['expected_event_id']!=EXPECTED_ID):
        return 'UNBOUND_IDENTITY'
    times=[record.get(k) for k in ('ack_tick','decision_tick','receipt_tick','verdict_tick')]
    if (not all(type(t) is int and t>=0 for t in times) or not times==sorted(times) or
            not times[0]<times[1]<=times[2]<times[3]):
        return 'TIMING_OR_REPLAY_INVALID'
    if (type(declared_lab_producer) is not bool or type(independent_receipt) is not bool or
            type(covered) is not bool or type(expected) is not bool or
            type(direct_edge) is not bool):
        return 'INVALID_ASSUMPTION_TYPE'
    if not expected:
        return 'NO_PREDECISION_EXPECTATION'
    if not covered:
        return 'NO_INDEPENDENT_COVERAGE'
    if not declared_lab_producer:
        return 'UNAUTHENTICATED_LAB_CLAIM'
    if not independent_receipt:
        return 'NOT_RECEIVED_BY_SHADOW_OBSERVER'
    return 'CONDITIONALLY_VISIBLE_IN_CLOSED_LAB_ONLY'


def analyze(n,nbytes,m,mbytes):
    a,b=_strict_report(n,nbytes,m,mbytes)
    world_records=[
      {'world_id':WORLD_IDS[0],
       'record':example_record('OPERATOR_VARIANT_SELECTED')},
      {'world_id':WORLD_IDS[1],
       'record':example_record('NO_VARIANT_SELECTED')},
    ]
    cases=[
      ('ingress_only',None,False,False,False,False,True),
      ('untrusted_payload',world_records[0]['record'],False,True,True,True,True),
      ('missing_receiver_receipt',world_records[0]['record'],True,False,True,True,True),
      ('without_predecision_expectation',world_records[0]['record'],True,True,True,False,True),
      ('without_coverage',world_records[0]['record'],True,True,False,True,True),
      ('closed_lab_conditionally_visible',world_records[0]['record'],True,True,True,True,True),
      ('indirect_C_cannot_claim_direct_A_link',dict(world_records[0]['record'],receiver='C'),True,True,True,True,False),
      ('stale_decision_receipt',dict(world_records[0]['record'],receipt_tick=5),True,True,True,True,True),
      ('mismatched_expected_event',dict(world_records[0]['record'],expected_event_id='shadow.other.event'),True,True,True,True,True),
      ('altered_episode',dict(world_records[0]['record'],episode_id='shadow.other.episode'),True,True,True,True,True),
    ]
    tested=[]
    for name,record,producer,receipt,cover,expect,direct in cases:
        status=inspect(record,declared_lab_producer=producer,
                 independent_receipt=receipt,covered=cover,expected=expect,direct_edge=direct)
        tested.append({'case':name,'classification':status,
                       'native_authority':False,'record_transmitted_in_native_spk':False})
    require([x['classification'] for x in tested]==[
       'NO_DECISION_RECORD','UNAUTHENTICATED_LAB_CLAIM',
       'NOT_RECEIVED_BY_SHADOW_OBSERVER','NO_PREDECISION_EXPECTATION',
       'NO_INDEPENDENT_COVERAGE','CONDITIONALLY_VISIBLE_IN_CLOSED_LAB_ONLY',
       'WRONG_DIRECT_EDGE','TIMING_OR_REPLAY_INVALID',
       'UNBOUND_IDENTITY','UNBOUND_IDENTITY'],
       'unexpected shadow decision classification')
    require(_project(a,N_TIERS[-1][1])==_project(b,N_TIERS[-1][1]),
            'T3 indistinguishability is not preserved')
    left,right=[inspect(x['record'],declared_lab_producer=True,
                          independent_receipt=True,covered=True,expected=True)
                for x in world_records]
    require(left==right=='CONDITIONALLY_VISIBLE_IN_CLOSED_LAB_ONLY' and
            world_records[0]['record']['action']!=world_records[1]['record']['action'],
            'conditional decision visibility demonstration failed')
    # Independent counterexample: the SAME declared action can coexist with
    # both distinct hypothetical hidden causes. Disclosure of a choice is
    # strictly weaker than proof of its causal effect on the missing event.
    same_action_record=example_record('OPERATOR_VARIANT_SELECTED')
    require(a['hidden_decision_cause']!=b['hidden_decision_cause'] and
            inspect(same_action_record,declared_lab_producer=True,
                    independent_receipt=True,covered=True,expected=True)==
                 'CONDITIONALLY_VISIBLE_IN_CLOSED_LAB_ONLY',
            'decision/causation counterexample failed')
    return {
      'schema':SCHEMA,'status':STATUS,
      'source_kind':'SOURCE_BOUND_NATIVE_POSTHOC_PLUS_SHADOW_DECISION_MESSAGES',
      'reference_v1n_sha256':sha256(nbytes).hexdigest(),
      'reference_v1m_sha256':sha256(mbytes).hexdigest(),
      'native_fixture_sha256':n['native_fixture_sha256'],
      'frozen_native_sources':n['frozen_native_sources'],
      'native_v1n_recomputation_verified_in_this_run':False,
      'native_scheduler_arms_inherited':4,
      'native_original_A_to_B':n['native_original_edge_A_B'],
      'native_variant_A_to_B':n['native_variant_edge_A_B'],
      'shadow_direct_link':EDGE,
      'T3_worlds_indistinguishable':True,
      'shadow_laboratory_record_differentiates_declared_actions_only':True,
      'shadow_actions_do_not_identify_causal_utility':True,
      'shadow_same_declared_decision_distinct_possible_causes':{
          'same_action':'OPERATOR_VARIANT_SELECTED',
          'hidden_cause_labels':[a['hidden_decision_cause'],b['hidden_decision_cause']],
          'cause_identified_by_decision_record':False,
          'worlds_native_executed':False},
      'shadow_case_count':len(tested),
      'shadow_case_classifications':tested,
      'shadow_decision_record_examples':world_records,
      'shadow_assumed_verification_is_not_authentication':True,
      'native_disclosure_channel_to_receiver_present':False,
      'native_authenticated_decision_records':0,
      'native_coverage_certificates':0,
      'native_absence_witnesses':0,
      'native_receiver_judgments':0,
      'native_sender_operator_updates':0,
      'native_learning_proven':False,
      'claims_excluded':EXCLUDED,
    }
