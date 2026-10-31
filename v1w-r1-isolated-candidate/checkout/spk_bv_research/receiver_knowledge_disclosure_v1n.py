"""BV v1n: finite receiver-knowledge lower bound, not a native disclosure channel.

A pure information-partition model bound to v1m's four actual native posthoc
traces. Only the *counts* in the native worlds are attested by those traces;
all hypothetical transport gaps, commitments, witnesses, and causes are
explicitly non-native laboratory possibilities. Nothing is delivered to B/C.
"""
from __future__ import annotations
from hashlib import sha256
import json
from spk_bv_research.off_on_v0t import require
from spk_bv_research.native_passive_trace_projection_v1m import (
    SCHEMA as M_SCHEMA, STATUS as M_STATUS, ROUTES,
)
from spk_bv_research.native_network_counterfactual_v1h import SCHEMA as H_SCHEMA, STATUS as H_STATUS
from spk_bv_research.native_route_lineage_v1g import SCHEMA as G_SCHEMA, STATUS as G_STATUS
from spk_bv_research.observer_closed_world_v1l import SCHEMA as L_SCHEMA, STATUS as L_STATUS

SCHEMA='spk-bv-source-bound-receiver-knowledge-disclosure-lower-bound/v1n'
STATUS='FINITE_EPISTEMIC_PARTITIONS_NO_NATIVE_DISCLOSURE_OR_JUDGMENT'
TIERS=(
    ('T0_INGRESS_ONLY', ('ingress_count',)),
    ('T1_PLUS_SENDER_PORT_DISCLOSURE', ('ingress_count','sender_port_count')),
    ('T2_PLUS_PREDECISION_EXPECTATION', ('ingress_count','sender_port_count','expected')),
    ('T3_PLUS_INDEPENDENT_INTERVAL_COVERAGE', ('ingress_count','sender_port_count','expected','covered')),
)
EXCLUDED=[
 'source-bound-scheduler-logs-not-receiver-readable-records',
 'tier-one-to-three-disclosures-not-transmitted-or-authenticated-in-native-SPK',
 'hypothetical-transport-gap-not-executed-in-frozen-native-scheduler',
 'shadow-precommit-and-coverage-not-real-testimonies',
 'same-ingress-projection-not-a-claim-of-identical-native-histories',
 'source-port-silence-not-sender-decision-cause',
 'synthetic-cause-labels-not-evidence-about-neuron-A',
 'no-native-absence-witness-endogenous-judgment-or-causal-credit',
 'no-operator-commit-learning-or-frozen-architecture-promotion',
]


def _world(name, ingress, emitted, expected, covered, cause, origin):
    require(type(name) is str and name and type(ingress) is int and ingress>=0
            and type(emitted) is int and emitted>=0 and ingress<=emitted
            and (expected is None or type(expected) is bool)
            and type(covered) is bool and type(cause) is str and type(origin) is str,
            'invalid finite-world definition')
    return {'world_id':name,'ingress_count':ingress,'sender_port_count':emitted,
            'expected':expected,'covered':covered,'hidden_decision_cause':cause,
            'world_origin':origin}


def _project(w, fields):
    require(all(key in w for key in fields),'unknown projection key')
    return tuple(w[key] for key in fields)


def _distinguishing_tier(a,b):
    require(type(a) is dict and type(b) is dict,'expected finite worlds')
    for tier,fields in TIERS:
        if _project(a,fields)!=_project(b,fields):
            return tier
    return 'NOT_DISTINGUISHABLE_THROUGH_T3'


def _canonical_json(report):
    return (json.dumps(report,sort_keys=True,indent=2,ensure_ascii=True,allow_nan=False)+'\n').encode()

def _validate_reference_dict(report, raw, schema, status, name):
    require(type(report) is dict and type(raw) is bytes and len(raw)>0
            and json.loads(raw)==report and raw==_canonical_json(report) and report.get('schema')==schema
            and report.get('status')==status,
            'invalid predecessor '+name)


def _edge_records(m, branch, mode):
    require(type(m['native_trace_projection']) is dict and
            set(m['native_trace_projection'])=={'original','variant'},
            'invalid branch set')
    arms=m['native_trace_projection'][branch]
    require(type(arms) is dict and set(arms)=={'off','on'},'invalid mode set')
    arm=arms[mode]
    require(type(arm) is dict and
            arm.get('native_full_scheduler_executed') is True and
            arm.get('posthoc_simulator_trace_reader_only') is True and
            arm.get('native_external_observer_present') is False and
            arm.get('native_absence_certificate_count')==0,
            'invalid posthoc arm authority')
    rows=arm.get('edge_projections')
    require(type(rows) is list and len(rows)==2,'expected exactly two native edges')
    out={}
    for item,(src,dst,sc,tc) in zip(rows,ROUTES):
        name=f'{src}->{dst}:{sc}->{tc}'
        require(type(item) is dict and item.get('edge')==name and
                item.get('sender')==src and item.get('receiver')==dst and
                item.get('sender_channel')==sc and item.get('receiver_channel')==tc and
                item.get('receiver_native_received_sender_port_attestation') is False and
                item.get('independent_two_port_coverage_certificate') is False,
                'edge identity/authority mismatch '+name)
        for field in ('sender_trace_emission_count',
                      'receiver_ingress_occurrence_count',
                      'receiver_consumed_occurrence_count'):
            require(type(item.get(field)) is int and item[field]>=0,
                    'invalid edge count '+field)
        t=item.get('sender_emission_timestamps'); ids=item.get('ingress_occurrence_ids')
        require(type(t) is list and all(type(v) is int and v>=0 for v in t) and
                t==sorted(t) and type(ids) is list and
                all(type(v) is str and v for v in ids) and len(set(ids))==len(ids),
                'invalid projection evidence lists')
        e=item['sender_trace_emission_count']; r=item['receiver_ingress_occurrence_count']
        require(e==r==item['receiver_consumed_occurrence_count']==len(t)==len(ids),
                'native posthoc count cannot join endpoint projection')
        require(item.get('posthoc_trace_classification')==(
              'ROUTED_EVENTS_IN_COMPLETE_RUN_TRACE' if e else
              'NO_SOURCE_CHANNEL_EVENT_IN_BOUNDED_RUN_TRACE'),
              'misclassified finite trace')
        out[name]=item
    return out


def analyze(m,mbytes,l,lbytes,h,hbytes,g,gbytes,d,dbytes):
    """Pure, source-bound analysis: no simulated disclosure becomes native evidence."""
    _validate_reference_dict(m,mbytes,M_SCHEMA,M_STATUS,'v1m')
    _validate_reference_dict(l,lbytes,L_SCHEMA,L_STATUS,'v1l')
    _validate_reference_dict(h,hbytes,H_SCHEMA,H_STATUS,'v1h')
    _validate_reference_dict(g,gbytes,G_SCHEMA,G_STATUS,'v1g1')
    require(type(d) is dict and type(dbytes) is bytes and dbytes and
            json.loads(dbytes)==d and dbytes==_canonical_json(d),'bad v1d reference')
    require(m.get('reference_v1l_sha256')==sha256(lbytes).hexdigest() and
            m.get('reference_v1h_sha256')==sha256(hbytes).hexdigest() and
            m.get('reference_v1g1_sha256')==sha256(gbytes).hexdigest() and
            m.get('reference_v1d_sha256')==sha256(dbytes).hexdigest() and
            l.get('reference_v1h_sha256')==sha256(hbytes).hexdigest() and
            h.get('reference_v1g1_file_sha256')==sha256(gbytes).hexdigest(),
            'predecessor reference SHA mismatch')
    require(m.get('source_kind')=='FROZEN_NATIVE_SCHEDULER_POSTHOC_TRACES' and
            m.get('full_native_scheduler_runs_recomputed_in_this_run')==4 and
            m.get('inherited_native_v1l_recomputation_verified_in_this_run') is True and
            m.get('native_coverage_certificates')==0 and
            m.get('endogenous_receiver_judgments')==0 and
            m.get('sender_operator_updates')==0 and
            m.get('native_learning_proven') is False and
            m.get('recipient_access_to_sender_trace_demonstrated') is False and
            m.get('native_two_port_independent_observer_installed') is False and
            m.get('cross_world_occurrence_identity_claimed') is False and
            m.get('causal_sender_decision_identified_by_receiver') is False,
            'native evidence is being promoted to unavailable receiver knowledge')
    require(l.get('lab_cases_native_attested')==0 and
            l.get('native_absence_witnesses')==0 and
            l.get('native_scored_receiver_judgments')==0 and
            l.get('native_updates_applied')==0 and
            l.get('learning_or_causal_utility_identified') is False and
            l.get('native_v1k_recomputation_verified_in_this_run') is True,
            'lab observer authority mismatch')
    require(h.get('real_variant_full_fabric_replay') is True and
            h.get('native_learning_proven') is False and
            h.get('native_updates_applied')==0 and
            h.get('native_scored_receiver_judgments')==0 and
            h.get('network_utility_identified') is False and
            h.get('conditional_direct_A_to_C') is False and
            g.get('original_forward_transport_grants_joined') is True and
            g.get('native_updates_applied')==0 and
            m.get('native_fixture_sha256')==h.get('native_fixture_sha256')==g.get('native_fixture_sha256') and
            m.get('frozen_native_sources')==h.get('frozen_native_sources')==g.get('frozen_native_sources'),
            'native source/counterfactual identity mismatch')
    rows={}
    for branch in ('original','variant'):
        rows[branch]={}
        for mode in ('off','on'):
            rows[branch][mode]=_edge_records(m,branch,mode)
            expected=2 if branch=='original' else 0
            require(all(e['sender_trace_emission_count']==expected and
                        e['receiver_ingress_occurrence_count']==expected
                        for e in rows[branch][mode].values()),
                    'source-bound native fixture count mismatch')
    require(rows['original']['off']==rows['original']['on'] and
            rows['variant']['off']==rows['variant']['on'],
            'forward endpoint projections changed under feedback')
    orig=rows['original']['off']; variant=rows['variant']['off']
    require(m.get('native_trace_source_emission_count_original_vs_variant')=={'A':[2,0],'B':[2,0]},
            'sender emission inventory drift')
    # B is the only direct receiver for A. C is B's receiver, never direct A->C.
    edge='A->B:7->0'
    native_original=orig[edge]; native_variant=variant[edge]
    require(native_original['sender_trace_emission_count']==2 and
            native_original['receiver_ingress_occurrence_count']==2 and
            native_variant['sender_trace_emission_count']==0 and
            native_variant['receiver_ingress_occurrence_count']==0,
            'native first edge drift')

    worlds=[
      _world('NATIVE_ORIGINAL_POSTHOC',2,2,None,False,'NOT_AVAILABLE','SOURCE_BOUND_NATIVE_TRACE_ONLY'),
      _world('NATIVE_VARIANT_POSTHOC',0,0,None,False,'NOT_AVAILABLE','SOURCE_BOUND_NATIVE_TRACE_ONLY'),
      _world('SHADOW_EMITTED_NOT_DELIVERED',0,2,True,True,'NOT_IDENTIFIED','HYPOTHETICAL_NOT_EXECUTED'),
      _world('SHADOW_EXPECTED_PORT_SILENCE',0,0,True,True,'NOT_IDENTIFIED','HYPOTHETICAL_NOT_EXECUTED'),
      _world('SHADOW_NO_PRECOMMIT',0,0,False,True,'NOT_IDENTIFIED','HYPOTHETICAL_NOT_EXECUTED'),
      _world('SHADOW_COVERAGE_LOSS',0,0,True,False,'NOT_IDENTIFIED','HYPOTHETICAL_NOT_EXECUTED'),
      _world('SHADOW_INTERNAL_CAUSE_A',0,0,True,True,'OPERATOR_CAUSE_ASSUMED','HYPOTHETICAL_NOT_EXECUTED'),
      _world('SHADOW_INTERNAL_CAUSE_B',0,0,True,True,'EXTERNAL_CAUSE_ASSUMED','HYPOTHETICAL_NOT_EXECUTED'),
    ]
    ids={x['world_id']:x for x in worlds}
    pairs=(
      ('NATIVE_VARIANT_POSTHOC','SHADOW_EMITTED_NOT_DELIVERED','T1_PLUS_SENDER_PORT_DISCLOSURE'),
      ('SHADOW_EXPECTED_PORT_SILENCE','SHADOW_EMITTED_NOT_DELIVERED','T1_PLUS_SENDER_PORT_DISCLOSURE'),
      ('SHADOW_EXPECTED_PORT_SILENCE','SHADOW_NO_PRECOMMIT','T2_PLUS_PREDECISION_EXPECTATION'),
      ('SHADOW_EXPECTED_PORT_SILENCE','SHADOW_COVERAGE_LOSS','T3_PLUS_INDEPENDENT_INTERVAL_COVERAGE'),
      ('SHADOW_INTERNAL_CAUSE_A','SHADOW_INTERNAL_CAUSE_B','NOT_DISTINGUISHABLE_THROUGH_T3'),
    )
    separations=[]
    for aid,bid,want in pairs:
        level=_distinguishing_tier(ids[aid],ids[bid])
        require(level==want,'invalid finite information partition')
        separations.append({'world_left':aid,'world_right':bid,
                            'first_distinguishable_at':level})
    partitions=[]
    for label,fields in TIERS:
        groups={}
        for w in worlds:
            key=_project(w,fields)
            groups.setdefault(key,[]).append(w['world_id'])
        partitions.append({'tier':label,'fields':list(fields),
                           'equivalence_classes':[sorted(names) for _,names in sorted(groups.items(),key=lambda kv:repr(kv[0]))],
                           'native_receiver_disclosure_available':False})
    return {
      'schema':SCHEMA,'status':STATUS,'source_kind':'NATIVE_SOURCE_BOUND_POSTHOC_PLUS_FINITE_NONNATIVE_WORLDS',
      'reference_v1m_sha256':sha256(mbytes).hexdigest(),
      'reference_v1l_sha256':sha256(lbytes).hexdigest(),
      'reference_v1h_sha256':sha256(hbytes).hexdigest(),
      'reference_v1g1_sha256':sha256(gbytes).hexdigest(),
      'reference_v1d_sha256':sha256(dbytes).hexdigest(),
      'native_fixture_sha256':m['native_fixture_sha256'],
      'frozen_native_sources':m['frozen_native_sources'],
      'native_v1m_recomputation_verified_in_this_run':False,
      'native_traces_in_v1m':4,
      'attested_direct_A_to_B':True,'attested_direct_A_to_C':False,
      'native_original_edge_A_B':{
        'sender_emissions':native_original['sender_trace_emission_count'],
        'receiver_ingress':native_original['receiver_ingress_occurrence_count']},
      'native_variant_edge_A_B':{
        'sender_emissions':native_variant['sender_trace_emission_count'],
        'receiver_ingress':native_variant['receiver_ingress_occurrence_count']},
      'native_full_two_port_observer_present':False,
      'native_disclosure_channel_to_receiver_present':False,
      'native_absence_witnesses':0,'native_scored_receiver_judgments':0,
      'native_operator_updates':0,'native_learning_proven':False,
      'shadow_worlds':worlds,'shadow_projection_tiers':partitions,
      'shadow_distinguishability_tests':separations,
      'shadow_tier_authority':'COUNTERFACTUAL_DISCLOSURE_MODEL_ONLY',
      'native_receiver_can_identify_missing_sender_decision':False,
      'shadow_same_ingress_can_have_distinct_emission_cause':True,
      'shadow_internal_cause_ambiguous_even_through_T3':True,
      'claims_excluded':EXCLUDED,
    }
