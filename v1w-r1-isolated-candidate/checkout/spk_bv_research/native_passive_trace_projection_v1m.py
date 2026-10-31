"""BV v1m: bounded native trace projections, NOT independent port witnesses.

Four frozen scheduler executions are read post hoc. An event in a producer-owned
trace is not a receiver-visible receipt, a signed observer record or a decision
provenance. Counters are reconciled with the whole-fabric v1h evidence.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
import json
from spk_bv_research.off_on_v0t import require,snapshot,summarize
from spk_bv_research.native_network_counterfactual_v1h import (
    SCHEMA as H_SCHEMA,STATUS as H_STATUS,variant_forward_audit)
from spk_bv_research.native_route_lineage_v1g import (
    SCHEMA as G_SCHEMA,STATUS as G_STATUS,_edge,_index_forward)
from spk_bv_research.observer_closed_world_v1l import SCHEMA as L_SCHEMA,STATUS as L_STATUS

SCHEMA='spk-bv-native-passive-two-port-trace-projection/v1m'
STATUS='NATIVE_POSTHOC_ENDPOINT_TRACES_NOT_INDEPENDENT_OBSERVER'
ROUTES=(('A','B',7,0),('B','C',7,0))
EXCLUDED=[
 'native-producer-owned-traces-do-not-constitute-independent-two-port-taps',
 'receiver-cannot-read-sender-emissions-without-a-new-authenticated-channel',
 'zero-events-in-finite-trace-do-not-certify-independent-absence-coverage',
 'no-cross-world-event-id-pairing-or-decision-cause-inference',
 'intervention-was-not-caused-by-neuronal-feedback',
 'no-native-absence-witness-or-endogenous-receiver-judgment',
 'no-utility-causal-credit-learning-or-operator-commit',
 'no-frozen-architecture-network-compiler-or-hardware-promotion',
]


def _extract(forward,edges):
    """Enforce strict accounting, including empty variant trace."""
    summary=variant_forward_audit(forward,edges)
    if forward['occurrences']:
        _,occ=_index_forward(forward,edges)
    else: occ=[]
    byid={x['id']:x for x in occ}
    batches=forward['batches']
    consumed=Counter(pid for b in batches for pid in b['parents'])
    require(set(consumed)==set(byid) and all(v==1 for v in consumed.values()),
            'forward ingress not consumed exactly once')
    for b in batches:
        require(type(b) is dict and type(b.get('node')) is str and
                type(b.get('tick')) is int and type(b.get('parents')) is list,
                'bad batch shape in trace')
    emissions=forward['emissions']
    require(all(type(e) is dict and type(e.get('node_id')) is str and
                type(e.get('timestamp')) is int and type(e.get('channel')) is int
                for e in emissions),'invalid emitted rows')
    require(all(x in ('A','B','C') for x in [e['node_id'] for e in emissions]),
            'foreign source in emitter trace')
    rows=[]
    for src,dst,sc,tc in ROUTES:
        m=[x for x in emissions if x['node_id']==src and x['channel']==sc]
        a=[x for x in occ if (x['source'],x['target'],x['sender_channel'],
                                x['receiver_channel'])==(src,dst,sc,tc)]
        # Strict multiplicity reconciliation is only valid on the frozen single
        # route per source/channel; reject topological drift.
        require(len(m)==len(a),'sender and receiver trace multiplicity mismatch')
        times=Counter(x['emitted_at'] for x in a)
        require(times==Counter(x['timestamp'] for x in m),
                'emission timestamp identity mismatch')
        rows.append({
           'edge':f'{src}->{dst}:{sc}->{tc}',
           'sender':src,'receiver':dst,'sender_channel':sc,'receiver_channel':tc,
           'sender_trace_emission_count':len(m),
           'receiver_ingress_occurrence_count':len(a),
           'receiver_consumed_occurrence_count':sum(consumed[x['id']] for x in a),
           'sender_emission_timestamps':sorted(x['timestamp'] for x in m),
           'ingress_occurrence_ids':[x['id'] for x in a],
           'posthoc_trace_classification':(
              'ROUTED_EVENTS_IN_COMPLETE_RUN_TRACE' if m else
              'NO_SOURCE_CHANNEL_EVENT_IN_BOUNDED_RUN_TRACE'),
           'receiver_native_received_sender_port_attestation':False,
           'independent_two_port_coverage_certificate':False,
        })
    return summary,rows,occ


def analyze(l,lbytes,h,hbytes,g,gbytes,d,dbytes,native,runs,owners,source_hashes):
    require(type(l) is dict and type(lbytes) is bytes and lbytes and
            json.loads(lbytes)==l and
            l.get('schema')==L_SCHEMA and l.get('status')==L_STATUS and
            l.get('native_v1k_recomputation_verified_in_this_run') is True and
            l.get('native_absence_witnesses')==0 and
            l.get('native_scored_receiver_judgments')==0 and
            l.get('native_updates_applied')==0 and
            l.get('lab_cases_native_attested')==0 and
            l.get('learning_or_causal_utility_identified') is False,
            'v1l reference is not a restricted lab report')
    require(type(h) is dict and type(hbytes) is bytes and hbytes and
            json.loads(hbytes)==h and
            h.get('schema')==H_SCHEMA and h.get('status')==H_STATUS and
            h.get('real_variant_full_fabric_replay') is True and
            h.get('native_updates_applied')==0 and
            h.get('native_scored_receiver_judgments')==0 and
            h.get('network_utility_identified') is False and
            h.get('variant_off_on_forward_outcomes_equal') is True and
            h.get('conditional_direct_A_to_C') is False,
            'v1h reference permits unsupported promotion')
    require(type(g) is dict and type(gbytes) is bytes and gbytes and
            json.loads(gbytes)==g and
            g.get('schema')==G_SCHEMA and g.get('status')==G_STATUS and
            g.get('original_forward_transport_grants_joined') is True and
            g.get('off_route_multiset_equal_on') is True and
            g.get('native_updates_applied')==0,
            'v1g1 route evidence invalid')
    require(type(d) is dict and type(dbytes) is bytes and dbytes and
            json.loads(dbytes)==d and
            h.get('reference_v1d_file_sha256')==sha256(dbytes).hexdigest(),
            'v1h selected candidate reference mismatch')
    require(l.get('reference_v1h_sha256')==sha256(hbytes).hexdigest() and
            l.get('reference_v1g1_sha256')==sha256(gbytes).hexdigest() and
            h.get('reference_v1g1_file_sha256')==sha256(gbytes).hexdigest(),
            'reference hashes drift')
    require(type(native) is tuple and len(native)==3 and
            snapshot(native)==h.get('native_fixture_sha256')==g.get('native_fixture_sha256') and
            type(owners) is dict and set(owners)=={'A','B','C'},
            'native fixture or owners mismatch')
    require(type(source_hashes) is dict and source_hashes==h.get('frozen_native_sources')
            and source_hashes==g.get('frozen_native_sources'),
            'frozen source provenance mismatch')
    routes=[_edge(x,owners) for x in native[1].static_routes]
    require(routes==g.get('static_routes') and
            [(x['source_node'],x['target_node'],x['source_channel'],x['target_channel'])
             for x in routes]==list(ROUTES),
            'expected native A-B-C chain changed')
    require(type(runs) is dict and set(runs)=={'original','variant'} and
            all(type(runs[k]) is dict and set(runs[k])=={'off','on'}
                for k in ('original','variant')),
            'four native runs are required')
    results={};orig_off_rows=[]
    for branch in ('original','variant'):
        results[branch]={}
        for mode in ('off','on'):
            run=runs[branch][mode]
            require(type(run) is dict and run.get('enabled') is (mode=='on') and
                    run.get('policy')=='forward-first' and type(run.get('forward')) is dict,
                    'native mode/policy mismatch')
            summary,rows,occ=_extract(run['forward'],routes)
            require(summary==h[branch][mode],
                    'complete native forward audit diverges from v1h '+branch+'/'+mode)
            digest=summarize(run,enabled=(mode=='on'),priority='forward-first')['whole_result_sha256']
            require(digest==h[branch][mode+'_result_sha256'],
                    'native whole-result SHA mismatch '+branch+'/'+mode)
            if branch=='original' and mode=='off':orig_off_rows=occ
            results[branch][mode]={
                'edge_projections':rows,
                'native_full_scheduler_executed':True,
                'posthoc_simulator_trace_reader_only':True,
                'native_external_observer_present':False,
                'native_absence_certificate_count':0,
            }
    require(orig_off_rows==g.get('original_off_occurrence_lineage'),
            'original forward identity/ancestry differs from v1g1')
    for mode in ('off','on'):
        original=results['original'][mode]['edge_projections']
        variant=results['variant'][mode]['edge_projections']
        require([x['sender_trace_emission_count'] for x in original]==[2,2] and
                [x['receiver_ingress_occurrence_count'] for x in original]==[2,2] and
                [x['sender_trace_emission_count'] for x in variant]==[0,0] and
                [x['receiver_ingress_occurrence_count'] for x in variant]==[0,0],
                'fixture-specific source/ingress count no longer matches v1h')
        require(all(x['independent_two_port_coverage_certificate'] is False for x in original+variant),
                'runtime traces cannot certify independent coverage')
    return {
      'schema':SCHEMA,'status':STATUS,'source_kind':'FROZEN_NATIVE_SCHEDULER_POSTHOC_TRACES',
      'reference_v1l_sha256':sha256(lbytes).hexdigest(),
      'reference_v1h_sha256':sha256(hbytes).hexdigest(),
      'reference_v1g1_sha256':sha256(gbytes).hexdigest(),
      'reference_v1d_sha256':sha256(dbytes).hexdigest(),
      'native_fixture_sha256':snapshot(native),'frozen_native_sources':source_hashes,
      'full_native_scheduler_runs_recomputed_in_this_run':4,
      'inherited_native_v1l_recomputation_verified_in_this_run':True,
      'native_trace_projection':results,
      'native_trace_source_emission_count_original_vs_variant':{'A':[2,0],'B':[2,0]},
      'native_coverage_certificates':0,'endogenous_receiver_judgments':0,
      'sender_operator_updates':0,'native_learning_proven':False,
      'recipient_access_to_sender_trace_demonstrated':False,
      'native_two_port_independent_observer_installed':False,
      'cross_world_occurrence_identity_claimed':False,
      'causal_sender_decision_identified_by_receiver':False,
      'claims_excluded':EXCLUDED,
    }
