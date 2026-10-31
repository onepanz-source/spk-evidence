"""BV v0u: source-bound link-capacity pressure scan on native BV v0e.

Research ONLY. No learning, hardware, global credit, or architecture promotion.
Do not silently drop rejected cells or infer equal effective dynamic workloads.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from pathlib import Path

from spk_bv_research.off_on_v0t import (
    EXCLUSIONS as V0T_EXCLUSIONS, InterventionError, _deltas, require,
    runtime_modules_bound, snapshot, source_pins, summarize,
)

SCHEMA = 'spk-bv-native-link-pressure-three-arm/v0u'
STATUS = 'SOURCE_BOUND_LINK_CAPACITY_MODEL_SCAN_ONLY'
# First cell must be the previously source-verified v0t baseline.
GRID = ((1, 1), (2, 1), (2, 2), (4, 1), (4, 2))
ARMS = (
    ('off', False, 'forward-first'),
    ('on_forward_first', True, 'forward-first'),
    ('on_feedback_first', True, 'feedback-first'),
)
EXCLUSIONS = sorted(set(V0T_EXCLUSIONS + [
    'not-a-hardware-bandwidth-or-throughput-measure',
    'capacity-change-not-strict-equal-effective-workload',
    'single-small-three-neuron-native-fixture',
    'pareto-is-local-to-selected-proxy-metrics',
    'model-intervention-not-empirical-external-causation',
]))


def valid_fixture(native):
    require(type(native) is tuple and len(native) == 3 and
            type(native[2]) is tuple and len(native[2]) == 4,
            'unexpected fixture contract')
    case, fabric, plans = native
    lplan = plans[3]
    require(is_dataclass(lplan) and not isinstance(lplan, type) and
            {f.name for f in fields(lplan)} >= {
                'fabric_slots_per_tick', 'link_slots_per_tick',
                'max_link_span_ticks', 'max_outbox_per_pe'},
            'unexpected link plan dataclass')
    require(type(lplan.fabric_slots_per_tick) is int and
            type(lplan.link_slots_per_tick) is int and
            lplan.fabric_slots_per_tick == 1 and lplan.link_slots_per_tick == 1,
            'baseline link plan is not pinned (1,1)')
    return case, fabric, plans


def _arm(executor, plan_type, case, fabric, plans, label, enabled, priority, base_hash, fixture):
    require(snapshot(fixture) == base_hash, f'fixture modified before {label}')
    control = plan_type(enabled=enabled, priority=priority)
    require(type(control.enabled) is bool and control.enabled is enabled and control.priority == priority,
            'native BV control plan did not preserve requested policy')
    # Any native rejection must be surfaced rather than silently selected away.
    outcome = executor(case, fabric, *plans, control)
    require(snapshot(fixture) == base_hash, f'fixture modified by {label}')
    report = summarize(outcome, enabled=enabled, priority=priority)
    records = outcome['feedback']['deliveries']
    require(all(type(row) is dict and type(row.get('tick')) is int for row in records),
            'invalid feedback delivery tick')
    report['last_feedback_delivery_tick'] = max((row['tick'] for row in records), default=None)
    return report


def nondominated_policies(report):
    """Local nondominance in (terminal tick penalty, fabric contention, feedback wait).

    No universal scalar weighting, no cross-cell comparison and no claim of optimality.
    """
    a = report['off']; f = report['on_forward_first']; b = report['on_feedback_first']
    out = {}
    for label, row in (('on_forward_first', f), ('on_feedback_first', b)):
        require(row['last_forward_terminal_tick'] is not None and a['last_forward_terminal_tick'] is not None,
                'empty terminal trace not suitable for local frontier')
        out[label] = (
            row['last_forward_terminal_tick'] - a['last_forward_terminal_tick'],
            row['metrics']['fabric_link_contention'],
            row['metrics']['feedback_grant_wait_sum'],
        )
    keep=[]
    for k,v in out.items():
        if not any(all(y <= x for x,y in zip(v, w)) and any(y < x for x,y in zip(v, w))
                   for name,w in out.items() if name != k):
            keep.append(k)
    return {'axes':['terminal_tick_delta_vs_off', 'fabric_link_contention', 'feedback_grant_wait_sum'],
            'coordinates':{k:list(v) for k,v in sorted(out.items())},
            'nondominated':sorted(keep)}


def scan(fixture_fn, executor, plan_type, *, root: Path, pin_sources=True):
    root = root.resolve(strict=True)
    pins_before = source_pins(root) if pin_sources else None
    if pin_sources:
        runtime_modules_bound(root, executor, fixture_fn, plan_type)
    require(is_dataclass(plan_type) and {f.name for f in fields(plan_type)} >= {'enabled','priority'},
            'unexpected BV control dataclass')
    native = fixture_fn()
    case, fabric, plans = valid_fixture(native)
    base_sha = snapshot(native)
    cells=[]
    for fabric_slots, direction_slots in GRID:
        require(snapshot(native) == base_sha, 'original fixture mutated before cell')
        altered = replace(plans[3], fabric_slots_per_tick=fabric_slots,
                          link_slots_per_tick=direction_slots)
        cell_plans = plans[:3] + (altered,)
        cell_input = (case, fabric, cell_plans)
        cell_sha = snapshot(cell_input)
        arms={}
        for label, enabled, priority in ARMS:
            arms[label] = _arm(executor, plan_type, case, fabric, cell_plans,
                               f'{fabric_slots}/{direction_slots}:{label}',
                               enabled, priority, cell_sha, cell_input)
            require(snapshot(native) == base_sha, 'original fixture mutated during scan')
        off, fw, fb = arms['off'], arms['on_forward_first'], arms['on_feedback_first']
        require(fw['metrics']['feedback_link_grants'] > 0 and fb['metrics']['feedback_link_grants'] > 0,
                'on-control produced no feedback; cell uninformative')
        cell={
            'link_capacity':{'fabric_slots_per_tick':fabric_slots,
                             'link_slots_per_tick':direction_slots},
            'shared_cell_input_sha256':cell_sha,
            'status':'THREE_ARMS_OBSERVED',
            'runs':arms,
            'interventions':{
                'toggle_enabled_only':_deltas(off,fw),
                'change_priority_only':_deltas(fw,fb),
                'off_to_feedback_first_combined':_deltas(off,fb),
            },
        }
        cell['local_proxy_frontier'] = nondominated_policies(arms)
        cells.append(cell)
    if pin_sources:
        require(source_pins(root) == pins_before, 'native producer source drift')
        runtime_modules_bound(root, executor, fixture_fn, plan_type)
    require(snapshot(native) == base_sha, 'original fixture mutated by scan')
    return {
        'schema':SCHEMA, 'status':STATUS,
        'source_sha256':pins_before,
        'original_fixture_sha256':base_sha,
        'same_fixture_before_after_every_run':True,
        'grid':[{'fabric_slots_per_tick':f, 'link_slots_per_tick':d} for f,d in GRID],
        'capacity_changes_only_link_plan':True,
        'cells':cells,
        'claims_excluded':EXCLUSIONS,
    }


def verify_v0t_baseline(report, reference):
    """Existing v0t native report is the *independent* baseline for GRID[0]."""
    require(type(report) is dict and report.get('schema') == SCHEMA, 'bad v0u report')
    require(type(reference) is dict and reference.get('schema') ==
            'spk-bv-native-three-arm-feedback/v0t' and
            reference.get('status') == 'SOURCE_BOUND_THREE_ARM_MODEL_INTERVENTION_ONLY',
            'invalid source v0t report')
    require(report['original_fixture_sha256'] == reference.get('shared_fixture_input_sha256'),
            'fixture differs from native v0t reference')
    require(type(report['cells']) is list and len(report['cells']) == len(GRID) and
            report['cells'][0]['link_capacity'] ==
                {'fabric_slots_per_tick':1,'link_slots_per_tick':1},
            'missing native baseline capacity cell')
    for k,_,_ in ARMS:
        cell_arm = report['cells'][0]['runs'][k]
        pinned = reference['runs'][k]
        for field in ('whole_result_sha256', 'forward_states_sha256',
                      'forward_emission_payload_multiset_sha256',
                      'forward_terminal_payload_multiset_sha256',
                      'last_forward_terminal_tick','metrics'):
            require(cell_arm[field] == pinned[field],
                    'v0u baseline does not replay pinned v0t: ' + k + '.' + field)
    require(reference.get('v0o_reference_check',{}).get('status') ==
            'PINNED_V0O_ON_RUNS_REPLAYED_IN_THREE_ARM',
            'v0t baseline lacks independently verified v0o replay')
    require(report['source_sha256'] == reference.get('producer_source_sha256'),
            'v0t and v0u source pins mismatch')
    return {'status':'PINNED_V0T_AND_V0O_BASELINE_REPLAYED',
            'reference_three_arm_hashes_equal':True,
            'original_fixture_equal':True,
            'source_pins_equal':True}
