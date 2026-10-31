"""BV v1k: receiver-local expectation protocol, proof-authority boundary.

This module does NOT attest a runtime witness. No user-supplied dict (even with
plausible timestamps, hashes or `authority`) can establish source authenticity.
It models admissibility of shadow observation and the unresolved causal gaps.
"""
from __future__ import annotations
from hashlib import sha256
import json
from spk_bv_research.off_on_v0t import require
from spk_bv_research.receiver_silence_observability_v1j import SCHEMA as J_SCHEMA, STATUS as J_STATUS

SCHEMA='spk-bv-receiver-local-absence-authority-boundary/v1k'
STATUS='SOURCE_BOUND_NO_NATIVE_ABSENCE_WITNESS_SHADOW_PROTOCOL_ONLY'
SHADOW_SCHEMA='spk-bv-declared-receiver-watch-protocol/v1k'
_FIELDS={
    'schema','expectation_id','episode_id','decision_id','sender','receiver',
    'sender_channel','receiver_channel','expected_count','commit_tick',
    'receiver_ack_tick','decision_tick','deadline_tick','coverage_start_tick',
    'coverage_end_tick','observed_until_tick','expected_event_ids','observed_ids','monitor_id',
    'criterion_id','authority'
}
CLAIMS_EXCLUDED=[
 'a-plausible-observer-dict-is-not-a-native-coverage-certificate',
 'hashes-are-content-identity-not-producer-authentication',
 'receiver-acknowledgment-is-declared-not-native-observed',
 'missing-expected-event-does-not-identify-sender-decision-or-cause',
 'a-receiver-local-direct-edge-does-not-establish-ancestral-C-witness',
 'shadow-example-does-not-modify-frozen-SPK-neuron-or-scheduler',
 'no-endogenous-scored-judgment-no-causal-credit-or-learning',
 'no-independent-causal-votes-no-hardware-or-architecture-promotion',
]

def _tick(x):return type(x) is int and 0 <= x <= 100000

def _identifier(x):
    return (type(x) is str and 1 <= len(x) <= 96 and
            all(c.isascii() and (c.isalnum() or c in '_.:-') for c in x))

def validate_shadow_protocol(p):
    """Validate declared *logic* but refuse to mint witness authority."""
    require(type(p) is dict and set(p)==_FIELDS,'shadow fields incomplete or unexpected')
    require(p['schema']==SHADOW_SCHEMA and p['authority']=='SHADOW_DECLARATION_ONLY',
            'only the explicit shadow declaration tier is supported')
    for k in ('expectation_id','episode_id','decision_id','sender','receiver','monitor_id','criterion_id'):
        require(_identifier(p[k]),'invalid identifier '+k)
    require(p['sender']=='A' and p['receiver']=='B' and
            type(p['sender_channel']) is int and p['sender_channel']==7 and
            type(p['receiver_channel']) is int and p['receiver_channel']==0,
            'receiver-local protocol requires the attested DIRECT A->B:7->0 route')
    require(p['monitor_id'] not in (p['sender'],p['receiver']),
            'shadow monitor must be distinct from sender/receiver (not evidence of independence)')
    for k in ('expected_count','commit_tick','receiver_ack_tick','decision_tick',
              'deadline_tick','coverage_start_tick','coverage_end_tick','observed_until_tick'):
        require(_tick(p[k]),'invalid tick or count '+k)
    require(1 <= p['expected_count'] <= 16,'positive bounded expectation required')
    require(p['commit_tick'] <= p['receiver_ack_tick'] < p['decision_tick'] < p['deadline_tick'],
            'expectation must be acknowledged before decision and deadline later')
    require(type(p['expected_event_ids']) is list and
            len(p['expected_event_ids'])==p['expected_count'] and
            all(_identifier(x) for x in p['expected_event_ids']) and
            len(p['expected_event_ids'])==len(set(p['expected_event_ids'])),
            'invalid expected event identity list')
    require(type(p['observed_ids']) is list and
            all(_identifier(x) for x in p['observed_ids']) and
            len(p['observed_ids'])==len(set(p['observed_ids'])) and
            set(p['observed_ids']).issubset(set(p['expected_event_ids'])),
            'observations must reference unique declared event identities')
    require(p['coverage_start_tick'] <= p['coverage_end_tick'] and
            p['coverage_end_tick'] <= p['observed_until_tick'],
            'incoherent coverage/horizon')
    # These conditions are still *claims* only. No local trust is minted.
    return p

def shadow_classification(p):
    validate_shadow_protocol(p)
    if p['observed_ids']:
        return 'DECLARED_EVENTS_SEEN_WITHOUT_NATIVE_AUTHORITY'
    if p['observed_until_tick'] < p['deadline_tick']:
        return 'DECLARED_EXPECTATION_PENDING'
    if (p['coverage_start_tick'] > p['decision_tick'] or
            p['coverage_end_tick'] < p['deadline_tick']):
        return 'DECLARED_COVERAGE_GAP'
    return 'DECLARED_EXPECTATION_MISSED_NO_NATIVE_CAUSAL_AUTHORITY'

def example_protocol(**changes):
    """A source-independent logical illustration, not an observation of v1h."""
    p={
      'schema':SHADOW_SCHEMA,'expectation_id':'shadow.exp.1',
      'episode_id':'shadow.future.episode','decision_id':'shadow.A.decision.1',
      'sender':'A','receiver':'B','sender_channel':7,'receiver_channel':0,
      'expected_count':1,'commit_tick':1,'receiver_ack_tick':2,
      'decision_tick':3,'deadline_tick':8,'coverage_start_tick':3,
      'coverage_end_tick':8,'observed_until_tick':8,
      'expected_event_ids':['shadow.future.event.1'],'observed_ids':[],
      'monitor_id':'shadow.monitor.1','criterion_id':'shadow.criterion.1',
      'authority':'SHADOW_DECLARATION_ONLY'
    }
    p.update(changes);return p

def audit(j,jbytes,*,v1i_bytes,v1h_bytes,v1g1_bytes,shadow=None):
    """An audit of provenance and observer authority; no native absence claim."""
    require(type(j) is dict and j.get('schema')==J_SCHEMA and j.get('status')==J_STATUS
            and j.get('native_v1i_recomputation_verified_in_this_run') is True
            and j.get('native_absence_witnesses')==0
            and j.get('native_scored_receiver_judgments')==0
            and j.get('shadow_absence_judgment_authorized') is False
            and j.get('sender_update_or_learning_proven') is False
            and j.get('absence_feedback_recoverable_from_variant_stream') is False,
            'v1j missing or claims unsupported source authority')
    require(all(type(b) is bytes and b for b in (jbytes,v1i_bytes,v1h_bytes,v1g1_bytes)),
            'missing source bytes')
    require(json.loads(jbytes)==j,'v1j decoded report does not match reference bytes')
    require(j['reference_v1i_sha256']==sha256(v1i_bytes).hexdigest() and
            j['reference_v1h_sha256']==sha256(v1h_bytes).hexdigest() and
            j['reference_v1g1_sha256']==sha256(v1g1_bytes).hexdigest(),
            'reference chain mismatch')
    observers=j.get('source_bound_observers')
    require(type(observers) is list and len(observers)==2,'unexpected receiver scope')
    for o,who,relation in zip(observers,('B','C'),('DIRECT_A_TO_B','DESCENDANT_VIA_B')):
        require(type(o) is dict and o.get('receiver')==who and
                o.get('relation_to_A')==relation and
                o.get('native_observed_original_incoming_occurrences')==2 and
                o.get('native_observed_variant_incoming_occurrences')==0 and
                o.get('predeclared_expectation_evidence_available') is False and
                o.get('coverage_and_deadline_witness_available') is False and
                o.get('native_criterion_available') is False and
                o.get('variant_judgment')=='NOT_IDENTIFIABLE_FROM_EVENT_ONLY_OBSERVATION' and
                o.get('independent_causal_vote') is False,
                'native receiver observer role/authority altered')
    native={'B':{'source':'A','direct':True,'missing_witnesses':True},
            'C':{'source':'B','direct_from_A':False,'missing_witnesses':True}}
    scenarios=[]
    if shadow is not None:
        require(type(shadow) is list and 1 <= len(shadow) <= 8,
                'shadow plans must be a small nonempty list')
        ids=set()
        for p in shadow:
            validate_shadow_protocol(p)
            key=(p['episode_id'],p['expectation_id'])
            require(key not in ids,'duplicate shadow expectation')
            ids.add(key)
            scenarios.append({
               'expectation_id':p['expectation_id'], 'episode_id':p['episode_id'],
               'receiver':p['receiver'], 'classification':shadow_classification(p),
               'logical_predecision_ack_declared':True,
               'expected_count_declared':p['expected_count'],
               'expected_event_ids_declared':list(p['expected_event_ids']),
               'native_expected_event_authenticated':False,
               'native_coverage_proof_available':False,
               'causal_sender_decision_identified':False,
               'native_judgment_authorized':False,
               'shadow_protocol_sha256':sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            })
    return {
      'schema':SCHEMA,'status':STATUS,
      'reference_v1j_sha256':sha256(jbytes).hexdigest(),
      'reference_v1i_sha256':sha256(v1i_bytes).hexdigest(),
      'reference_v1h_sha256':sha256(v1h_bytes).hexdigest(),
      'reference_v1g1_sha256':sha256(v1g1_bytes).hexdigest(),
      'native_v1j_recomputation_verified_in_this_run':False,
      'native_absence_witnesses':0,'endogenous_receiver_judgments':0,
      'native_updates_applied':0,'causal_credit_or_learning_proven':False,
      'receiver_local_direct_scope':native,
      'shadow_plan_supplied':shadow is not None,'shadow_scenarios':scenarios,
      'shadow_scenarios_native_attested':0,
      'witness_authority_barrier':'UNTRUSTED_JSON_CANNOT_CERTIFY_NATIVE_EVENT_ABSENCE',
      'required_implementation_contract':[
        'independent_source-attested-decision-schedule-or-commitment',
        'receiver-predecision-receipt-of-expectation',
        'source-attested-full-interval-coverage-and-observable-clock',
        'noncircular-watch-channel-independent-of-monitored-spike-delivery',
        'causal-binding-of-missing-identifier-to-the-sender-decision',
        'receiver-native-predeclared-value-criterion',
      ],
      'claims_excluded':CLAIMS_EXCLUDED,
    }
