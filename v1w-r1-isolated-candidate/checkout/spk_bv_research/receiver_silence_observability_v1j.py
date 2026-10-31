"""BV v1j: bounded receiver-event observability, not sender-absence knowledge.

No event-only receiver can conclude why an event was not observed. Shadow
expectations and deadlines are declarations, not source-attested measurements.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
from spk_bv_research.off_on_v0t import require
from spk_bv_research.native_feedback_silence_v1i import audit as audit_i, SCHEMA as I_SCHEMA, STATUS as I_STATUS
from spk_bv_research.native_network_counterfactual_v1h import SCHEMA as H_SCHEMA, STATUS as H_STATUS
from spk_bv_research.native_route_lineage_v1g import SCHEMA as G_SCHEMA, STATUS as G_STATUS

SCHEMA='spk-bv-receiver-silence-observability-contract/v1j'
STATUS='SOURCE_BOUND_EVENT_ONLY_SILENCE_NOT_RECEIVER_JUDGMENT'
EXCLUSIONS=[
 'lack-of-event-does-not-identify-why-no-event-arrived',
 'original-vs-variant-branch-known-to-experimenter-not-native-receiver',
 'shadow-expected-events-not-externally-attested-expectations',
 'deadline-and-coverage-declarations-not-native-monitoring-witnesses',
 'original-feedback-lineage-is-not-an-endogenous-scored-judgment',
 'zero-variant-feedback-does-not-indicate-approval-or-disapproval',
 'two-recipients-share-forward-causal-ancestry-not-independent-votes',
 'no-operator-update-or-rollback-or-learning-or-causal-utility',
 'no-new-hardware-network-topology-or-architecture-promotion',
]

def nat(x):return type(x) is int and 0 <= x <= 100000

def classify_silence(*, received, expected=None, deadline=None, observed_until=None,
                     coverage_declared=False):
    """Classify claims conservatively; a declared expectation is never a native witness.

    Expected is not an observed event count. All temporal parameters are
    integer ticks, not wall-clock times. The result never claims utility.
    """
    require(nat(received),'invalid observed event count')
    require(expected is None or nat(expected),'invalid shadow expectation')
    require(deadline is None or nat(deadline),'invalid shadow deadline')
    require(observed_until is None or nat(observed_until),'invalid observation horizon')
    require(type(coverage_declared) is bool,'invalid coverage declaration')
    require((deadline is None)==(observed_until is None),
            'deadline and horizon must be supplied together')
    require(expected is not None or (deadline is None and not coverage_declared),
            'unsolicited timing or coverage without expectation')
    if received:
        return 'OBSERVED_EVENTS_NO_UTILITY_INFERRED'
    if expected is None or expected==0:
        return 'SILENCE_WITHOUT_POSITIVE_EXPECTATION'
    if deadline is None:
        return 'UNRESOLVED_SHADOW_EXPECTATION_NO_DEADLINE'
    if observed_until < deadline:
        return 'PENDING_SHADOW_EXPECTATION'
    if not coverage_declared:
        return 'UNCOVERED_SHADOW_EXPECTATION'
    return 'MISSED_DECLARED_EXPECTATION_NOT_SOURCE_ATTESTED'


def _validate_g(g):
    require(type(g) is dict and g.get('schema')==G_SCHEMA and g.get('status')==G_STATUS
            and g.get('original_forward_transport_grants_joined') is True
            and g.get('off_route_multiset_equal_on') is True
            and g.get('original_off_occurrences')==4 and g.get('original_on_occurrences')==4
            and g.get('native_feedback_assessment_count')==2
            and g.get('native_reverse_delivery_count')==4
            and g.get('endogenous_receiver_judgments')==0
            and g.get('native_updates_applied')==0,
            'original native event/feedback attestation changed')
    edges=g.get('static_routes')
    require(type(edges) is list and len(edges)==2,'unexpected static routing scope')
    normalized=Counter((e.get('source_node'),e.get('source_channel'),e.get('target_node'),
                        e.get('target_channel'),e.get('source_pe'),e.get('target_pe'),
                        e.get('delay_ticks')) for e in edges if type(e) is dict)
    require(normalized==Counter({('A',7,'B',0,'PE0','PE1',1):1,
                                 ('B',7,'C',0,'PE1','PE2',1):1}),
            'A->B->C route identity mismatch')
    rows=g.get('original_off_occurrence_lineage')
    require(type(rows) is list and len(rows)==4,'incomplete original occurrences')
    byid={}
    for r in rows:
        require(type(r) is dict and type(r.get('id')) is str and r['id'] not in byid
                and type(r.get('parents')) is list and
                all(nat(r.get(x)) for x in ('emitted_at','delivered_at','sender_channel','receiver_channel'))
                and r['emitted_at'] <= r['delivered_at'],
                'invalid original occurrence')
        byid[r['id']]=r
    require(Counter((r['source'],r['target'],r['sender_channel'],r['receiver_channel']) for r in rows)
            ==Counter({('A','B',7,0):2,('B','C',7,0):2}),
            'original occurrence edge counts inconsistent')
    parent_counts=Counter()
    for r in rows:
        ps=r['parents']
        require(len(ps)==len(set(ps)) and all(type(q) is str and q in byid for q in ps),
                'invalid occurrence parent references')
        if r['source']=='A':
            require(ps==[],'A first-hop unexpectedly has a parent')
        else:
            require(len(ps)==1 and byid[ps[0]]['source']=='A' and
                    byid[ps[0]]['target']=='B' and
                    byid[ps[0]]['delivered_at']<=r['emitted_at'],
                    'B->C not supported by causal A->B origin')
            parent_counts[ps[0]]+=1
    require(len(parent_counts)==2 and all(x==1 for x in parent_counts.values()),
            'causal provenance multiplicity incorrect')
    return byid


def _validate_feedback(g,byid):
    rev=g.get('native_reverse_deliveries')
    require(type(rev) is list and len(rev)==4,'wrong reverse delivery count')
    edge_counts=Counter()
    by_assessment={}
    for rec in rev:
        require(type(rec) is dict and type(rec.get('assessment_id')) is str and
                type(rec.get('sender')) is str and type(rec.get('receiver')) is str and
                type(rec.get('evidence_ids')) is list and
                len(rec['evidence_ids'])==1 and nat(rec.get('delivered_at')) and
                type(rec.get('native_independent_receiver_flag')) is bool,
                'bad native reverse delivery structure')
        src,dst=rec['sender'],rec['receiver']
        edge_counts[(src,dst)]+=1
        oid=rec['evidence_ids'][0]
        require(type(oid) is str and oid in byid,'unknown reverse delivery origin')
        o=byid[oid]
        require((src,dst)==(o['target'],o['source']) and
                rec['delivered_at']>o['delivered_at'],
                'reverse feedback not bound to causal forward occurrence')
        key=rec['assessment_id']
        arm=by_assessment.setdefault(key,{})
        require((src,dst) not in arm, 'duplicate reverse relay for assessment')
        arm[(src,dst)]=(oid,rec['delivered_at'])
        # Native reverse deliveries are relays; they do not certify independence.
    require(edge_counts==Counter({('C','B'):2,('B','A'):2}),
            'reverse relay directions/multiplicities incorrect')
    require(len(by_assessment)==2, 'unexpected number of actual assessments')
    for aid, relay in by_assessment.items():
        require(set(relay)=={('C','B'),('B','A')},
                'assessment missing its corresponding feedback relay')
        c_oid,c_tick=relay[('C','B')];b_oid,b_tick=relay[('B','A')]
        require(byid[c_oid]['parents']==[b_oid] and c_tick < b_tick,
                'assessment reverse path not bound to same original causal branch')
    return edge_counts


def audit(v1i,v1i_bytes,*,v1h,v1h_bytes,v1g1,v1g1_bytes,v1d_bytes):
    """Bind v1j to a source-recomputed v1i and an attested original route lineage."""
    require(all(type(x) is bytes and x for x in
                (v1i_bytes,v1h_bytes,v1g1_bytes,v1d_bytes)),
            'missing reference byte evidence')
    require(type(v1i) is dict and v1i.get('schema')==I_SCHEMA and
            v1i.get('status')==I_STATUS and
            v1i.get('native_v1h_recomputation_verified_in_this_run') is True,
            'v1i lacks source-bound native replay attestation')
    require(type(v1h) is dict and v1h.get('schema')==H_SCHEMA and
            v1h.get('status')==H_STATUS and
            v1h.get('real_variant_full_fabric_replay') is True,
            'v1h lacks native full network intervention')
    require(v1i['reference_v1h_sha256']==sha256(v1h_bytes).hexdigest() and
            v1i['reference_v1g1_sha256']==sha256(v1g1_bytes).hexdigest() and
            v1i['reference_v1d_sha256']==sha256(v1d_bytes).hexdigest(),
            'source chain SHA-256 mismatch')
    require(v1h.get('reference_v1g1_file_sha256')==sha256(v1g1_bytes).hexdigest() and
            v1h.get('reference_v1d_file_sha256')==sha256(v1d_bytes).hexdigest(),
            'v1h source links mismatch')
    reconstruct=audit_i(v1h,v1h_bytes,g_bytes=v1g1_bytes,d_bytes=v1d_bytes)
    reconstruct['native_v1h_recomputation_verified_in_this_run']=True
    require(v1i==reconstruct,'v1i report not equal to recomputed boundary')
    byid=_validate_g(v1g1)
    rev=_validate_feedback(v1g1,byid)
    require(v1g1.get('conditional_receiver_route_audit')==[
        {'receiver_id':'B','direct_static_route_7_to_0':True,
         'direct_original_forward_occurrences':2,
         'observed_original_forward_ancestry_from_A':True,
         'v1e_variant_network_route_replayed':False,
         'native_criterion_or_judgment_from_receiver':False},
        {'receiver_id':'C','direct_static_route_7_to_0':False,
         'direct_original_forward_occurrences':0,
         'observed_original_forward_ancestry_from_A':True,
         'v1e_variant_network_route_replayed':False,
         'native_criterion_or_judgment_from_receiver':False}],
         'receiver source role drift')
    origin=v1h['original']['off'];variant=v1h['variant']['off']
    require(origin['edges']=={'A->B:7->0':2,'B->C:7->0':2} and
            variant['edges']=={} and origin['occurrences']==4 and
            variant['occurrences']==0 and variant['batches']==2 and
            v1h['native_feedback_assessments']=={'original_on':2,'variant_on':0} and
            v1h['native_feedback_deliveries']=={'original_on':4,'variant_on':0},
            'native original/variant exposure mismatch')
    require(v1i.get('variant_receiver_judgment_sign')=='UNOBSERVED_NOT_NEUTRAL_OR_POSITIVE' and
            v1i.get('native_scored_receiver_judgments')==0 and
            v1i.get('native_updates_applied')==0 and
            v1i.get('learning_proven') is False,
            'source reclassifies silence as value or learning')
    scopes=[]
    for neuron,relation,upstream in (('B','DIRECT_A_TO_B','A'),('C','DESCENDANT_VIA_B','B')):
        scopes.append({
         'receiver':neuron,'relation_to_A':relation,
         'native_observed_original_incoming_occurrences':origin['edges'][f'{upstream}->{neuron}:7->0'],
         'native_observed_variant_incoming_occurrences':variant['edges'].get(f'{upstream}->{neuron}:7->0',0),
         'original_observation':classify_silence(received=2),
         'variant_observation':classify_silence(received=0),
         'native_criterion_available':False,
         'predeclared_expectation_evidence_available':False,
         'coverage_and_deadline_witness_available':False,
         'variant_judgment':'NOT_IDENTIFIABLE_FROM_EVENT_ONLY_OBSERVATION',
         'independent_causal_vote':False})
    # This is only a logical illustration. The second world was not run by SPK.
    indistinguishability={
      'observer_model':'INGRESS_EVENT_ONLY',
      'observed_variant_B_ingress_events':0,
      'hypothetical_worlds_same_receiver_projection':[
        'A_COMPUTES_BUT_SUPPRESSES_EMISSION',
        'NO_CAUSAL_A_EVENT_REACHES_B_FOR_AN_UNSPECIFIED_OTHER_REASON'],
      'alternative_world_reexecuted_in_native_scheduler':False,
      'no_sender_cause_inference_from_empty_observation':True,
    }
    return {
      'schema':SCHEMA,'status':STATUS,
      'reference_v1i_sha256':sha256(v1i_bytes).hexdigest(),
      'reference_v1h_sha256':sha256(v1h_bytes).hexdigest(),
      'reference_v1g1_sha256':sha256(v1g1_bytes).hexdigest(),
      'reference_v1d_sha256':sha256(v1d_bytes).hexdigest(),
      'native_v1i_recomputation_verified_in_this_run':False,
      'original_native_routes_and_feedback_verified':True,
      'source_bound_observers':scopes,
      'original_assessments_native':2,
      'original_reverse_deliveries_native':sum(rev.values()),
      'variant_native_assessments':0,
      'variant_native_reverse_deliveries':0,
      'native_scored_receiver_judgments':0,
      'native_absence_witnesses':0,
      'absence_feedback_recoverable_from_variant_stream':False,
      'shadow_absence_judgment_authorized':False,
      'sender_update_or_learning_proven':False,
      'experimental_logical_indistinguishability':indistinguishability,
      'minimal_future_contract_fields':[
        'declared_upstream_expectation_bound_before_episode',
        'source_authenticated_expected_event_identity',
        'independently_observable_deadline',
        'coverage_certificate_including_missing_event_interval',
        'receiver_predeclared_value_criterion',
        'event_or_missingness_to_sender_decision_causal_binding',
      ],
      'claims_excluded':EXCLUSIONS,
    }
