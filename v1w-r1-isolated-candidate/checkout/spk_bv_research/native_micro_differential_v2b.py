"""v2b: bounded native-v1q/m vs micro-v2a differential falsification.

Counts can coincide in 16 source-attested native *reports* and bounded micro
replays while timestamp order disproves trace-equivalence in the original.
No frozen-native runs or authentication/receiver delivery occur in this module.
"""
from __future__ import annotations

from hashlib import sha256

from spk_bv_research.off_on_v0t import require
from spk_bv_research.native_allocation_boundary_v1r import validate_q, canon
from spk_bv_research.native_passive_trace_projection_v1m import (
    SCHEMA as M_SCHEMA, STATUS as M_STATUS)
from spk_bv_research.versioned_executor_admission_v2a import (
    SCHEMA as A_SCHEMA, STATUS as A_STATUS, SOURCE_KIND as A_SOURCE,
    analyze as rebuild_a, assert_observation_stream)
from spk_backvalidation_v2.observed_scheduler_v2a import (
    BoundedCaseV2a, ObserverV2a, execute_live_v2a, NODES)
from spk_bv_research.native_capture_v0k import canonical_fixture, _json_bytes

SCHEMA = 'spk-bv-native-micro-finite-differential-boundary/v2b'
STATUS = 'FINITE_COUNT_ALIGNMENT_AND_ORIGINAL_TEMPORAL_COUNTEREXAMPLE'
SOURCE = 'PRIOR_NATIVE_V1Q_V1M_POSTHOC_PLUS_REEXECUTED_V2A_MICRO'
ARMS = ('none','A','B','C','AB','AC','BC','ABC')
MODES = ('off','on')
EDGES = (('A', 'B', 'A->B:7->0'), ('B', 'C', 'B->C:7->0'))
EXCLUDED = [
    'count-alignment-is-not-SPK-CMP-operator-semantic-equivalence',
    'micro-A-block-is-not-native-CMP2-even-when-all-fixture-counts-match',
    'native-timestamps-from-v1m-are-posthoc-not-receiver-knowledge',
    'micro-ordinal-is-not-native-clock-or-event-identity',
    'relative-sender-emission-order-differs-in-bounded-original-fixture',
    'no-native-state-BV-feedback-or-scheduling-equivalence-demonstrated',
    'no-independent-absence-coverage-producer-authentication-or-B-delivery',
    'no-native-judgment-value-criterion-operator-update-or-learning',
    'no-new-frozen-scheduler-executions-or-frozen-source-modifications',
]


def operators_for(arm):
    require(type(arm) is str and arm in ARMS, 'unsupported native intervention')
    # Intentional count-fitting representation, NOT SPK opcode equivalence.
    return tuple('block' if n == 'A' and 'A' in arm else
                 'pair' if n in arm else 'relay' for n in NODES)


def validate_reports(a, ab, q, qb, m, mb, z, zb, y, yb, x, xb,
                     source_sha256):
    for obj, raw in ((a,ab),(q,qb),(m,mb),(z,zb),(y,yb),(x,xb)):
        require(type(obj) is dict and type(raw) is bytes and raw == canon(obj),
                'noncanonical report or untrusted input bytes')
    require(type(source_sha256) is str and len(source_sha256)==64 and
            all(c in '0123456789abcdef' for c in source_sha256),
            'invalid bounded executor source pin')
    validate_q(q, qb)
    require(q['native_fixture_sha256'] == m.get('native_fixture_sha256') and
            q['frozen_native_sources'] == m.get('frozen_native_sources') and
            m.get('schema') == M_SCHEMA and m.get('status') == M_STATUS and
            m.get('source_kind') == 'FROZEN_NATIVE_SCHEDULER_POSTHOC_TRACES' and
            m.get('full_native_scheduler_runs_recomputed_in_this_run') == 4 and
            m.get('native_two_port_independent_observer_installed') is False and
            m.get('native_coverage_certificates') == 0 and
            m.get('endogenous_receiver_judgments') == 0 and
            m.get('sender_operator_updates') == 0 and
            m.get('native_learning_proven') is False and
            m.get('cross_world_occurrence_identity_claimed') is False,
            'v1m native trace or no-authority boundary invalid')
    require(a.get('schema') == A_SCHEMA and a.get('status') == A_STATUS and
            a.get('source_kind') == A_SOURCE and
            a.get('frozen_native_source_pins_rechecked_in_this_run') is True and
            a.get('versioned_executor_file_sha256') == source_sha256 and
            a.get('reference_v1z_sha256') == sha256(zb).hexdigest() and
            a.get('reference_v1y_sha256') == sha256(yb).hexdigest() and
            a.get('reference_v1x_sha256') == sha256(xb).hexdigest() and
            a.get('frozen_native_forward_equivalence_proven') is False and
            a.get('frozen_native_BV_equivalence_proven') is False and
            a.get('native_recipient_B_received_control_messages') == 0,
            'unauthorized v2a source or semantic promotion')
    reproduced = rebuild_a(z,zb,y,yb,x,xb, frozen_source_custody=True,
                           executor_sha256=source_sha256)
    require(a == reproduced and ab == canon(reproduced),
            'v2a report fails byte-identical micro recomputation')
    ym = y.get('native_probe_parity_matrix')
    require(type(ym) is dict and set(ym) == {'original','variant'},
            'native baseline source provenance missing')
    for arm, origin in (('none','original'),('A','variant')):
        for mode in MODES:
            r = q['factorial_runs'][arm][mode]
            yr = ym[origin][mode]
            require(r['native_result_sha256'] == yr['probe_result_sha256'] ==
                    yr['no_probe_result_sha256'] and
                    yr['native_return_bytes_equal'] is True,
                    'native source matrix is not v1y attested fixture')
    traces = m.get('native_trace_projection')
    require(type(traces) is dict and set(traces) == {'original','variant'},
            'native original/variant temporal traces missing')
    for origin, arm in (('original','none'),('variant','A')):
        require(type(traces[origin]) is dict and set(traces[origin])==set(MODES),
                'native trace modes incomplete')
        for mode in MODES:
            r = traces[origin][mode]
            require(type(r) is dict and
                    r.get('native_full_scheduler_executed') is True and
                    r.get('posthoc_simulator_trace_reader_only') is True and
                    r.get('native_external_observer_present') is False and
                    r.get('native_absence_certificate_count') == 0 and
                    type(r.get('edge_projections')) is list and
                    len(r['edge_projections']) == 2,
                    'native finite trace is not posthoc source-bound')
            for idx, (_, _, edge) in enumerate(EDGES):
                er = r['edge_projections'][idx]
                count = q['factorial_runs'][arm][mode]['edges'][edge]
                ts = er.get('sender_emission_timestamps')
                require(er.get('edge') == edge and
                        er.get('sender') == EDGES[idx][0] and
                        er.get('receiver') == EDGES[idx][1] and
                        er.get('sender_trace_emission_count') == count and
                        er.get('receiver_ingress_occurrence_count') == count and
                        er.get('receiver_consumed_occurrence_count') == count and
                        type(ts) is list and len(ts)==count and
                        all(type(t) is int and t>=0 for t in ts) and
                        ts == sorted(ts) and len(set(ts))==len(ts) and
                        er.get('receiver_native_received_sender_port_attestation') is False and
                        er.get('independent_two_port_coverage_certificate') is False,
                        'native trace counts/port or timestamps drift')
    return True


def _native_order(projections):
    events=[]
    for er in projections:
        for t in er['sender_emission_timestamps']:
            events.append((t, er['sender']))
    require(len(set(t for t,_ in events)) == len(events),
            'native source timestamps tied: ordering unresolved')
    return ''.join(src for t,src in sorted(events))


def compare(a, ab, q, qb, m, mb, z, zb, y, yb, x, xb, source_sha256,
            *, frozen_custody=False):
    require(type(frozen_custody) is bool, 'invalid frozen custody flag')
    validate_reports(a,ab,q,qb,m,mb,z,zb,y,yb,x,xb,source_sha256)
    records=[]
    for arm in ARMS:
        ops=operators_for(arm)
        for mode in MODES:
            case=BoundedCaseV2a('diff.v2b.'+arm+'.'+mode,(1,1),ops,mode=='on')
            off=execute_live_v2a(case)
            port=ObserverV2a()
            on=execute_live_v2a(case, observation_port=port)
            require(_json_bytes(canonical_fixture(off))==
                    _json_bytes(canonical_fixture(on)),
                    'new micro observer changed result')
            assert_observation_stream(case,port,on)
            native=q['factorial_runs'][arm][mode]
            nr=native['emissions_by_neuron']
            nedge=native['edges']
            require(on['forward_emissions']==nr and
                    on['forward_routes']=={'A->B':nedge['A->B:7->0'],
                                            'B->C':nedge['B->C:7->0']} and
                    on['forward_terminal_count']==native['forward']['terminal'],
                    'finite micro/native count projection differs')
            records.append({'arm':arm,'mode':mode,'micro_operators':list(ops),
                            'micro_emissions_by_neuron':on['forward_emissions'],
                            'micro_edges':on['forward_routes'],
                            'micro_terminal':on['forward_terminal_count'],
                            'native_feedback_assessments_not_reproduced':
                                native['feedback_assessments'],
                            'micro_observer_records':len(port.events),
                            'count_projection_equal':True,
                            'native_state_semantics_equal':None})
    require(len(records)==16, 'incomplete native-micro comparison')
    original=[]
    for mode in MODES:
        case=BoundedCaseV2a('order.v2b.'+mode,(1,1),('relay',)*3,mode=='on')
        port=ObserverV2a()
        result=execute_live_v2a(case,observation_port=port)
        assert_observation_stream(case,port,result)
        micro=''.join(e.actor for e in port.events if
                      e.phase=='sender_port_emission' and e.actor in ('A','B'))
        native=_native_order(m['native_trace_projection']['original'][mode]
                             ['edge_projections'])
        require(micro=='AABB' and native=='ABAB' and micro!=native,
                'bounded original order witness no longer demonstrates mismatch')
        original.append({'bv_mode':mode, 'native_posthoc_sender_order':native,
                         'micro_live_sender_order':micro,
                         'order_equal':False,
                         'event_identifiers_joinable_across_runtimes':False})
    return {
        'schema':SCHEMA, 'status':STATUS, 'source_kind':SOURCE,
        'reference_v2a_sha256':sha256(ab).hexdigest(),
        'reference_v1q_sha256':sha256(qb).hexdigest(),
        'reference_v1m_sha256':sha256(mb).hexdigest(),
        'reference_v1z_sha256':sha256(zb).hexdigest(),
        'reference_v1y_sha256':sha256(yb).hexdigest(),
        'reference_v1x_sha256':sha256(xb).hexdigest(),
        'frozen_native_source_pins_rechecked_in_this_run':frozen_custody,
        'versioned_executor_file_sha256':source_sha256,
        'prior_native_factorial_runs_attested_in_v1q':16,
        'new_native_scheduler_executions_in_v2b':0,
        'micro_off_on_executions_in_v2b':32,
        'count_projection_cells_equal':16,
        'count_alignment':records,
        'original_temporal_counterexample':original,
        'original_trace_order_equivalence_disproven_in_fixture':True,
        'native_cmp_semantics_equivalence_proven':False,
        'native_state_equivalence_proven':False,
        'native_BV_equivalence_proven':False,
        'native_receiver_B_control_packets':0,
        'native_independent_absence_certificates':0,
        'native_scored_receiver_judgments':0,
        'native_operator_updates':0,
        'native_learning_proven':False,
        'no_cross_world_event_identity_claimed':True,
        'claims_excluded':EXCLUDED,
    }
