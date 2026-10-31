"""v2c differential causal-time scheduling experiment; finite fitted witness.

Demonstrates an independently declared bounded time-ordered micro policy
which can match the prior *posthoc* A/B native timestamps on one fixture.
Not an implementation, inference or verification of native scheduler policy.
"""
from __future__ import annotations
from hashlib import sha256

from spk_bv_research.off_on_v0t import require
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_micro_differential_v2b import (
    SCHEMA as B_SCHEMA, STATUS as B_STATUS, SOURCE as B_SOURCE,
    compare as replay_b, operators_for, ARMS, MODES, _native_order,
)
from spk_bv_research.native_capture_v0k import canonical_fixture, _json_bytes
from spk_backvalidation_v2.observed_scheduler_v2a import (
    BoundedCaseV2a, ObserverV2a, ObservationV2a, PORT_VERSION, NODES,
)
from spk_backvalidation_v2.time_order_executor_v2c import (
    TemporalPolicyV2c, execute_time_order_v2c, EXECUTOR_VERSION,
)

SCHEMA = 'spk-bv-bounded-causal-time-micro-differential/v2c'
STATUS = 'FITTED_ORIGINAL_AB_TIMESTAMPS_NO_NATIVE_SCHEDULING_EQUIVALENCE'
SOURCE_KIND = 'SOURCE_BOUND_NATIVE_POSTHOC_V1M_PLUS_INDEPENDENT_TIME_ORDER_MICRO'
EXCLUDED = [
    'micro-input-gap-and-hop-delay-are-experimenter-selected-after-native-evidence',
    'fitted-A-B-timestamps-are-not-inferred-frozen-scheduler-policy',
    'source-owned-micro-observations-are-not-native-events-or-receiver-messages',
    'matching-A-B-projection-is-not-full-event-trace-or-state-equivalence',
    'relay-pair-block-are-not-CMP-and-BV-on-is-label-only',
    'same-logical-tick-does-not-prove-native-simultaneity-or-coverage',
    'no-native-authentication-or-absence-witness-or-operator-learning',
    'no-new-native-runs-and-no-frozen-source-modifications',
]


def assert_stream(case, policy, result, port):
    """Independent structural/cause audit of executor records, not native proof."""
    es = port.events
    require(not port.overflow and not port.sink_fault and len(es) > 0 and
            len(es) == result['logical_event_count'] and
            es[-1].phase == 'interval_coverage_close', 'incomplete micro stream')
    require(result.get('executor_version') == EXECUTOR_VERSION and
            result.get('episode') == case.episode and
            result.get('bv_label_only') is case.bv_enabled and
            result.get('receiver_B_control_packets') == 0 and
            result.get('native_feedback_assessments') == 0 and
            result.get('operator_updates') == 0,
            'unauthorized runtime or receiver promotion')
    require(result['policy'] == {'stimulus_gap':policy.stimulus_gap,
                                'hop_delay':policy.hop_delay,
                                'tie_break':'CREATION_SEQUENCE'}, 'policy swapped')
    require(all(type(e) is ObservationV2a and e.version == PORT_VERSION and
                e.episode == case.episode and e.ordinal == i and
                type(e.logical_tick) is int and e.logical_tick > 0 and
                (i==0 or e.logical_tick >= es[i-1].logical_tick)
                for i,e in enumerate(es)), 'micro event identity/order mismatch')
    require(sum(e.phase == 'interval_coverage_close' for e in es)==1,
            'bad local interval closure')
    decisions=result['decisions']
    ids={d['decision_id']:d for d in decisions}
    require(len(ids)==len(decisions)==result['forward_decisions'],
            'invalid independent decision ledger')
    seen_emissions={}; expected_emissions={n:0 for n in NODES}
    arrivals={n:0 for n in NODES}; tick_list={n:[] for n in NODES}
    route_count={'A->B':0,'B->C':0}
    declared=set()
    decided=set()
    for i,e in enumerate(es[:-1]):
        require(e.phase in {'receiver_ingress','predecision_expectation','decision',
                            'sender_port_emission'}, 'unknown phase')
        if e.phase=='receiver_ingress':
            require(e.actor in ('B','C') and e.target==NODES[NODES.index(e.actor)-1] and
                    e.parent_token == e.event_token and e.event_token in seen_emissions and
                    seen_emissions[e.event_token] == (e.target, e.logical_tick-policy.hop_delay),
                    'unowned ingress or wrong route latency')
            arrivals[e.actor]+=1
            tick_list[e.actor].append(e.logical_tick)
            route_count[f'{e.target}->{e.actor}']+=1
        elif e.phase=='predecision_expectation':
            require(e.actor in NODES and e.decision_id in ids and
                    ids[e.decision_id]['node']==e.actor and
                    ids[e.decision_id]['tick']==e.logical_tick and
                    e.decision_id not in declared,
                    'unexpected or duplicated local predecision')
            declared.add(e.decision_id)
            if e.actor=='A':
                arrivals['A']+=1;tick_list['A'].append(e.logical_tick)
        elif e.phase=='decision':
            require(e.decision_id in declared and e.decision_id not in decided and
                    e.actor == ids[e.decision_id]['node'] and
                    e.logical_tick == ids[e.decision_id]['tick'] and
                    e.parent_token == ids[e.decision_id]['parent'],
                    'unbound local decision')
            decided.add(e.decision_id)
        elif e.phase=='sender_port_emission':
            d=ids.get(e.decision_id)
            require(type(d) is dict and d['selected'] is True and
                    e.decision_id in decided and
                    e.actor==d['node'] and e.logical_tick==d['tick'] and
                    e.parent_token==d['parent'] and
                    e.target==(NODES[NODES.index(e.actor)+1] if e.actor!='C' else 'TERMINAL') and
                    e.event_token==f'{case.episode}.{e.actor}.e{expected_emissions[e.actor]+1}' and
                    e.event_token not in seen_emissions,
                    'spurious or repeated emission')
            seen_emissions[e.event_token]=(e.actor,e.logical_tick)
            expected_emissions[e.actor]+=1
    require(len(declared)==len(ids) and decided==declared, 'missing decision')
    for d in decisions:
        require(d['selected']==(d['operator']=='relay' or
                (d['operator']=='pair' and int(d['decision_id'].rsplit('d',1)[-1])%2==0)) and
                d['operator'] in ('relay','pair','block'), 'operator decision inconsistent')
        actual=sum(e.phase=='sender_port_emission' and
                   e.decision_id==d['decision_id'] for e in es)
        require(actual==int(d['selected']), 'missing or duplicated decision emission')
    require(arrivals==result['forward_arrivals'] and
            expected_emissions==result['forward_emissions'] and
            route_count==result['forward_routes'] and
            tick_list==result['arrival_ticks'] and
            all(result['emission_ticks'][n]==[
                e.logical_tick for e in es if e.phase=='sender_port_emission' and e.actor==n]
                for n in NODES) and
            len(result['forward_terminal_tokens'])==result['forward_terminal_count'],
            'emission/ingress/result ledger inconsistent')
    return True


def paired(case,policy, *, capacity=512, sink=None):
    off=execute_time_order_v2c(case,policy=policy)
    p=ObserverV2a(capacity=capacity,sink=sink)
    on=execute_time_order_v2c(case,policy=policy,observation_port=p)
    require(_json_bytes(canonical_fixture(off)) ==
            _json_bytes(canonical_fixture(on)), 'observer altered bounded result')
    if p.summary()['complete']:
        assert_stream(case,policy,on,p)
    return on,p


def validate_predecessor(b,bb,a,ab,q,qb,m,mb,z,zb,y,yb,x,xb,sha_a):
    require(all(type(o) is dict and type(raw) is bytes and raw==canon(o)
                for o,raw in ((b,bb),(a,ab),(q,qb),(m,mb),(z,zb),(y,yb),(x,xb))),
            'noncanonical predecessor bytes')
    require(b.get('schema')==B_SCHEMA and b.get('status')==B_STATUS and
            b.get('source_kind')==B_SOURCE and
            b.get('count_projection_cells_equal')==16 and
            b.get('frozen_native_source_pins_rechecked_in_this_run') is True and
            b.get('original_trace_order_equivalence_disproven_in_fixture') is True and
            b.get('native_cmp_semantics_equivalence_proven') is False and
            b.get('new_native_scheduler_executions_in_v2b')==0 and
            b.get('reference_v2a_sha256')==sha256(ab).hexdigest() and
            b.get('reference_v1q_sha256')==sha256(qb).hexdigest() and
            b.get('reference_v1m_sha256')==sha256(mb).hexdigest(),
            'v2b provenance or false authority')
    rebuilt=replay_b(a,ab,q,qb,m,mb,z,zb,y,yb,x,xb,sha_a,
                     frozen_custody=True)
    require(canon(rebuilt)==bb,'v2b did not recompute byte-identically')
    return True


def analyze(b,bb,a,ab,q,qb,m,mb,z,zb,y,yb,x,xb,sha_a,sha_c,
            *, frozen_custody=False):
    require(type(frozen_custody) is bool and all(type(h) is str and len(h)==64 and
            all(c in '0123456789abcdef' for c in h) for h in (sha_a,sha_c)),
            'invalid source pins')
    validate_predecessor(b,bb,a,ab,q,qb,m,mb,z,zb,y,yb,x,xb,sha_a)
    policy=TemporalPolicyV2c(2,1)
    records=[]
    for arm in ARMS:
        for mode in MODES:
            case=BoundedCaseV2a('time.v2c.'+arm+'.'+mode,(1,1),
                                 operators_for(arm),mode=='on')
            result,port=paired(case,policy)
            native=q['factorial_runs'][arm][mode]
            require(result['forward_emissions']==native['emissions_by_neuron'] and
                    result['forward_routes']=={
                        'A->B':native['edges']['A->B:7->0'],
                        'B->C':native['edges']['B->C:7->0']} and
                    result['forward_terminal_count']==native['forward']['terminal'],
                    'finite counts drift under time-order policy')
            row={'arm':arm,'mode':mode,'emissions':result['forward_emissions'],
                 'routes':result['forward_routes'],'terminal':result['forward_terminal_count'],
                 'time_order_micro_observer_records':len(port.events),
                 'micro_source_owned_events_during_execution':True,
                 'observer_off_on_typed_result_bytes_equal':True,
                 'native_counts_equal_in_finite_fixture':True}
            if arm in ('none','A'):
                origin='original' if arm=='none' else 'variant'
                native_edges=m['native_trace_projection'][origin][mode]['edge_projections']
                na=native_edges[0]['sender_emission_timestamps']
                nb=native_edges[1]['sender_emission_timestamps']
                require(result['emission_ticks']['A']==na and
                        result['emission_ticks']['B']==nb,
                        'time-order fit fails prior native A/B timestamps')
                row['posthoc_native_AB_timestamp_projection_equal']=True
            else:
                row['posthoc_native_AB_timestamp_projection_equal']=None
            records.append(row)
    require(len(records)==16,'incomplete finite differential')
    original=[]
    for mode in MODES:
        case=BoundedCaseV2a('schedule.v2c.original.'+mode,(1,1),
                             ('relay',)*3,mode=='on')
        baseline,port=paired(case,policy)
        emitted=''.join(e.actor for e in port.events if
                        e.phase=='sender_port_emission' and e.actor in ('A','B'))
        native=_native_order(m['native_trace_projection']['original'][mode]
                             ['edge_projections'])
        require(emitted==native=='ABAB','original order fit not reproduced')
        # A different input cadence defeats timestamp equality; v2a FIFO
        # likewise remains a valid count model but was an order counterexample.
        other,_=paired(case,TemporalPolicyV2c(3,1))
        require(other['emission_ticks']['A']==[1,4] and
                other['emission_ticks']['B']==[2,5] and
                other['emission_ticks']['A']!=baseline['emission_ticks']['A'],
                'temporal-pacing negative control failed')
        original.append({
            'mode':mode,'native_posthoc_AB_sender_order':native,
            'time_order_micro_AB_sender_order':emitted,
            'native_posthoc_A_emission_ticks':[1,3],
            'micro_A_emission_ticks':baseline['emission_ticks']['A'],
            'native_posthoc_B_emission_ticks':[2,4],
            'micro_B_emission_ticks':baseline['emission_ticks']['B'],
            'counterfactual_gap3_micro_A_ticks':other['emission_ticks']['A'],
            'counterfactual_gap3_micro_B_ticks':other['emission_ticks']['B'],
            'order_equal_in_original_fixture':True,
            'timing_inference_or_native_policy_equivalence_proven':False,
        })
    return {
        'schema':SCHEMA,'status':STATUS,'source_kind':SOURCE_KIND,
        'reference_v2b_sha256':sha256(bb).hexdigest(),
        'reference_v2a_sha256':sha256(ab).hexdigest(),
        'reference_v1q_sha256':sha256(qb).hexdigest(),
        'reference_v1m_sha256':sha256(mb).hexdigest(),
        'reference_v1z_sha256':sha256(zb).hexdigest(),
        'reference_v1y_sha256':sha256(yb).hexdigest(),
        'reference_v1x_sha256':sha256(xb).hexdigest(),
        'frozen_native_source_pins_rechecked_in_this_run':frozen_custody,
        'micro_v2a_source_sha256':sha_a,'time_order_micro_v2c_source_sha256':sha_c,
        'temporal_policy_experimenter_selected':{
            'first_stimulus_tick':1,'stimulus_gap':2,'hop_delay':1,
            'tie_break':'CREATION_SEQUENCE'},
        'native_original_AB_order_observed_posthoc':'ABAB',
        'v2a_fifo_original_AB_order_prior':'AABB',
        'v2c_time_order_original_AB_order':'ABAB',
        'original_mode_order_and_AB_tick_projection_fit_count':2,
        'native_micro_count_projection_fit_count':16,
        'time_order_micro_observer_off_on_pairs':16,
        'time_order_micro_scheduler_runs':32,
        'new_frozen_scheduler_runs':0,
        'finite_rows':records,'original_timestamp_controls':original,
        'input_gap_perturbation_disproves_generalized_timestamp_identity':True,
        'native_CMP_semantics_equivalent':False,
        'native_BV_state_or_scheduling_equivalence_proven':False,
        'real_native_B_receives_micro_observer_events':False,
        'native_authenticated_producer_events':0,
        'native_independent_absence_certificates':0,
        'native_receiver_scored_judgments':0,'native_operator_updates':0,
        'native_learning_proven':False,
        'claims_excluded':EXCLUDED,
    }
