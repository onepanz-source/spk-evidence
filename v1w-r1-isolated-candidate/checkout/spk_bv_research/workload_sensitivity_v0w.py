"""BV v0w: source-bound temporal workload sensitivity of bounded v0e scheduler.

Research ONLY. Same frozen three-neuron architecture, nonadaptive programs,
shared experimental input per OFF/ON triple. Stimulus timing and multiplicity
are intentionally varied *between* workload cells. No causal learning claims.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from pathlib import Path

from spk_bv_research.off_on_v0t import (
    _deltas, require, runtime_modules_bound, snapshot, source_pins,
)
from spk_bv_research.link_pressure_v0u import ARMS, _arm
from spk_bv_research.inflight_pressure_v0v import validate_transport

SCHEMA = 'spk-bv-native-temporal-workload-three-arm/v0w'
STATUS = 'SOURCE_BOUND_TEMPORAL_WORKLOAD_MODEL_SCAN_ONLY'
# Native fixture has exactly two externally injected events at ticks 1 and 3.
# The fifth case repeats the complete two-event episode with an 8-tick shift.
WORKLOADS = ('baseline', 'coincident', 'second_plus_1', 'second_plus_3', 'repeated_episode')
# (fabric grants/tick, max cross-PE in-flight): isolate two independent limits.
CAPACITY_PROFILES = ((1, 4), (2, 1), (2, 4))
EXCLUSIONS = [
    'single-bounded-three-neuron-fixture-not-N-node-scalability',
    'stimulus-timing-changes-effective-workload',
    'identical-within-cell-inputs-not-identical-dynamic-work-per-policy',
    'repeated-episode-not-independent-trials',
    'forward-emission-equality-not-informational-value',
    'no-learning-or-neuron-program-adaptation',
    'no-global-causal-credit-or-policy-optimality',
    'no-hardware-latency-throughput-or-energy',
    'no-architecture-promotion',
    'no-v0h-528-stress-equivalence',
]


def _validate_events(case):
    require(is_dataclass(case) and not isinstance(case, type), 'native case is not dataclass')
    require('events' in {f.name for f in fields(case)}, 'case missing events')
    events = case.events
    require(type(events) is tuple and len(events) == 2, 'expected exactly two native external events')
    for event in events:
        require(is_dataclass(event) and not isinstance(event, type) and
                {'timestamp', 'node_id', 'channel'} <= {f.name for f in fields(event)},
                'unexpected external event dataclass')
        require(type(event.timestamp) is int and type(event.node_id) is str and
                type(event.channel) is int, 'invalid external event fields')
    require(tuple(e.timestamp for e in events) == (1, 3),
            'native baseline event timestamps changed')
    return events


def make_workload(case, name):
    events = _validate_events(case)
    first, second = events
    if name == 'baseline':
        altered = events
    elif name == 'coincident':
        altered = (first, replace(second, timestamp=first.timestamp))
    elif name == 'second_plus_1':
        altered = (first, replace(second, timestamp=second.timestamp + 1))
    elif name == 'second_plus_3':
        altered = (first, replace(second, timestamp=second.timestamp + 3))
    elif name == 'repeated_episode':
        altered = events + tuple(replace(e, timestamp=e.timestamp + 8) for e in events)
    else:
        require(False, 'unsupported workload label')
    require(type(altered) is tuple and all(type(e) is type(first) for e in altered),
            'workload changed event types')
    altered_case = replace(case, events=altered)
    require(snapshot(altered_case) == snapshot(replace(case, events=altered)),
            'non-deterministic workload rewrite')
    # Only externally injected events vary: all other case fields stay unchanged.
    require(snapshot(replace(altered_case, events=events)) == snapshot(case),
            'workload rewrite modified non-event case fields')
    return altered_case


def scan(fixture_fn, executor, plan_type, *, root: Path, pin_sources=True):
    root = root.resolve(strict=True)
    pins_before = source_pins(root) if pin_sources else None
    if pin_sources:
        runtime_modules_bound(root, executor, fixture_fn, plan_type)
    require(is_dataclass(plan_type) and {'enabled','priority'} <= {f.name for f in fields(plan_type)},
            'unexpected BV plan')
    native = fixture_fn()
    case, fabric, plans = validate_transport(native)
    _validate_events(case)
    original_sha = snapshot(native)
    rows = []
    for workload in WORKLOADS:
        changed_case = make_workload(case, workload)
        workload_sha = snapshot(changed_case)
        for cap, inflight_cap in CAPACITY_PROFILES:
            require(snapshot(native) == original_sha, 'native original fixture mutated before cell')
            link = replace(plans[3], fabric_slots_per_tick=cap)
            transport = replace(plans[0], max_inflight_occurrences=inflight_cap)
            cell_plans = (transport,) + plans[1:3] + (link,)
            cell_input = (changed_case, fabric, cell_plans)
            cell_sha = snapshot(cell_input)
            run = {}
            for label, enabled, priority in ARMS:
                captured = []
                def observe_executor(*args):
                    output = executor(*args)
                    contention = output.get('resources',{}).get('contention')
                    require(type(contention) is dict, 'native contention reasons missing')
                    require(all(type(k) is str and type(v) is int and v >= 0
                                for k,v in contention.items()),
                            'invalid native contention reason value')
                    captured.append(dict(sorted(contention.items())))
                    return output
                # Do not hide quota/rejection failures. They invalidate a complete-cell claim.
                run[label] = _arm(observe_executor, plan_type, changed_case, fabric, cell_plans,
                                  workload + f'/fabric={cap}/inflight={inflight_cap}/' + label,
                                  enabled, priority, cell_sha, cell_input)
                require(len(captured)==1, 'unexpected native result multiplicity')
                require(captured[0].get('fabric_link',0)==run[label]['metrics']['fabric_link_contention'],
                        'reported fabric contention differs from native counter')
                run[label]['contention_by_reason'] = captured[0]
                require(snapshot(native) == original_sha, 'native original fixture mutated by run')
                require(snapshot(changed_case) == workload_sha, 'rewritten case mutated by run')
            off, forward, feedback = (run['off'],run['on_forward_first'],run['on_feedback_first'])
            rows.append({
                'workload':workload,
                'stimulus_count':len(changed_case.events),
                'stimulus_timestamps':[e.timestamp for e in changed_case.events],
                'fabric_slots_per_tick':cap,
                'max_inflight_occurrences':inflight_cap,
                'shared_cell_input_sha256':cell_sha,
                'rewritten_case_sha256':workload_sha,
                'runs':run,
                'interventions':{
                    'toggle_enabled_only':_deltas(off,forward),
                    'change_priority_only':_deltas(forward,feedback),
                    'off_to_feedback_first_combined':_deltas(off,feedback),
                },
                'status':'COMPLETE_THREE_ARM_WORKLOAD_CELL',
            })
    if pin_sources:
        require(source_pins(root)==pins_before, 'native producer source SHA changed')
        runtime_modules_bound(root, executor, fixture_fn, plan_type)
    require(snapshot(native)==original_sha, 'native original fixture mutated after scan')
    return {
        'schema':SCHEMA,'status':STATUS,'source_sha256':pins_before,
        'original_fixture_sha256':original_sha,
        'same_fixture_before_after_every_run':True,
        'variation_scope':'external_event_timestamps_and_episode_repetition_only',
        'resource_scope':'capacity_profiles_((1,4),(2,1),(2,4))_other_plans_unchanged',
        'workloads':list(WORKLOADS),
        'capacity_profiles':[{'fabric_slots_per_tick':a,'max_inflight_occurrences':b}
                             for a,b in CAPACITY_PROFILES],
        'cells':rows,'claims_excluded':EXCLUSIONS,
    }


def verify_v0v_anchors(report, reference):
    """Three baseline capacity profiles must equal their corresponding native v0v cells."""
    require(type(report) is dict and report.get('schema')==SCHEMA and
            report.get('status')==STATUS, 'invalid v0w report')
    require(type(reference) is dict and
            reference.get('schema')=='spk-bv-native-link-inflight-factorial/v0v' and
            reference.get('status')=='SOURCE_BOUND_LINK_INFLIGHT_MODEL_FACTORIAL_ONLY',
            'invalid v0v native reference')
    require(reference.get('v0u_reference_check',{}).get('status')==
            'TWO_NATIVE_V0U_CAPACITY_CELLS_REPLAYED' and
            reference['v0u_reference_check'].get('v0u_v0t_v0o_reference_chain') is True,
            'reference lacks v0u/v0t/v0o native chain')
    require(reference.get('same_fixture_before_after_every_run') is True and
            report.get('same_fixture_before_after_every_run') is True,
            'fixture integrity absent')
    require(report.get('source_sha256')==reference.get('source_sha256') and
            report.get('original_fixture_sha256')==reference.get('original_fixture_sha256'),
            'native source/fixture drift')
    require(type(reference.get('cells')) is list and len(reference['cells'])==6 and
            type(report.get('cells')) is list and len(report['cells'])==len(WORKLOADS)*len(CAPACITY_PROFILES),
            'invalid reference or workload grid')
    for i, ((cap, inflight), ref_index) in enumerate(zip(CAPACITY_PROFILES, (0,4,1))):
        a, b = report['cells'][i],reference['cells'][ref_index]
        require(a['workload']=='baseline' and a['fabric_slots_per_tick']==cap and
                a['max_inflight_occurrences']==inflight and
                b['capacity']['fabric_slots_per_tick']==cap and
                b['capacity']['max_inflight_occurrences']==inflight,
                'baseline control mismatch')
        require(a['shared_cell_input_sha256']==b['shared_cell_input_sha256'],
                'baseline input SHA mismatch')
        for name,_,_ in ARMS:
            x,y = a['runs'][name],b['runs'][name]
            for key in ('whole_result_sha256','metrics','last_forward_terminal_tick',
                        'last_feedback_delivery_tick','forward_states_sha256',
                        'forward_emission_payload_multiset_sha256',
                        'forward_terminal_payload_multiset_sha256'):
                require(x[key]==y[key], f'baseline native output drift {cap}.{name}.{key}')
    return {'status':'THREE_NATIVE_V0V_REFERENCE_CELLS_REPLAYED',
            'v0v_v0u_v0t_v0o_chain':True,
            'anchors':[{'fabric_slots_per_tick':c,'max_inflight_occurrences':i} for c,i in CAPACITY_PROFILES]}
