"""BV v0v: source-bound link/inflight capacity interaction on native v0e.

Strictly abstract, three-node, model-internal intervention; no adaptation.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from pathlib import Path

from spk_bv_research.off_on_v0t import (
    _deltas, require, runtime_modules_bound, snapshot, source_pins,
)
from spk_bv_research.link_pressure_v0u import ARMS, _arm, valid_fixture

SCHEMA = 'spk-bv-native-link-inflight-factorial/v0v'
STATUS = 'SOURCE_BOUND_LINK_INFLIGHT_MODEL_FACTORIAL_ONLY'
# First two cells are independently pinned to v0u capacities 1/1 and 2/1,
# with native transport in-flight cap of 4 (the original v0e fixture).
GRID = ((1, 4), (2, 4), (1, 1), (1, 2), (2, 1), (2, 2))
EXCLUSIONS = [
    'bounded-three-neuron-native-v0e-only',
    'not-transport-hardware-bandwidth-or-buffer-bytes',
    'not-general-capacity-threshold-proof',
    'not-N-node-scalability',
    'no-learning-or-informational-benefit',
    'not-equal-effective-dynamic-workloads-between-capacity-cells',
    'no-global-causal-credit',
    'no-architecture-promotion',
    'no-v0h-528-stress-equivalence',
    'no-hardware-latency-energy',
]


def validate_transport(native):
    case, fabric, plans = valid_fixture(native)
    tp = plans[0]
    require(is_dataclass(tp) and not isinstance(tp,type) and
            {'max_inflight_occurrences','cross_pe_extra_ticks'} <= {f.name for f in fields(tp)},
            'unexpected transport plan dataclass')
    cap = tp.max_inflight_occurrences
    require(type(cap) is int and cap == 4, 'original transport max_inflight must equal 4')
    return case, fabric, plans


def scan(fixture_fn, executor, plan_type, *, root: Path, pin_sources=True):
    root = root.resolve(strict=True)
    before = source_pins(root) if pin_sources else None
    if pin_sources:
        runtime_modules_bound(root, executor, fixture_fn, plan_type)
    require(is_dataclass(plan_type) and
            {'enabled','priority'} <= {f.name for f in fields(plan_type)},
            'unexpected native BV plan')
    original = fixture_fn()
    case,fabric,plans = validate_transport(original)
    original_sha = snapshot(original)
    rows=[]
    for link_cap, inflight_cap in GRID:
        require(snapshot(original)==original_sha,'original fixture mutated before cell')
        altered_transport = replace(plans[0], max_inflight_occurrences=inflight_cap)
        altered_link = replace(plans[3], fabric_slots_per_tick=link_cap)
        cell_plans = (altered_transport,plans[1],plans[2],altered_link)
        cell_input = (case,fabric,cell_plans)
        cell_sha = snapshot(cell_input)
        run={}
        for name,enabled,priority in ARMS:
            # Reject bounded-horizon failures; never silently discard a cell.
            run[name] = _arm(executor,plan_type,case,fabric,cell_plans,
                             f'link={link_cap}/inflight={inflight_cap}:{name}',
                             enabled,priority,cell_sha,cell_input)
            require(run[name]['metrics']['peak_cross_inflight'] <= inflight_cap,
                    'scheduler reported peak exceeding transport limit')
            require(snapshot(original)==original_sha,'original fixture mutated during scan')
        a,b,c=run['off'],run['on_forward_first'],run['on_feedback_first']
        require(a['metrics']['feedback_link_grants']==0 and
                b['metrics']['feedback_link_grants']>0 and
                c['metrics']['feedback_link_grants']>0,
                'missing expected OFF/ON contrast')
        rows.append({
            'capacity':{'fabric_slots_per_tick':link_cap,
                        'max_inflight_occurrences':inflight_cap,
                        'directional_link_slots_per_tick':plans[3].link_slots_per_tick},
            'shared_cell_input_sha256':cell_sha,
            'runs':run,
            'interventions':{
                'toggle_enabled_only':_deltas(a,b),
                'change_priority_only':_deltas(b,c),
                'off_to_feedback_first_combined':_deltas(a,c),
            },
            'status':'COMPLETE_THREE_ARM_CAPACITY_CELL',
        })
    if pin_sources:
        require(source_pins(root)==before,'native producer SHA drift')
        runtime_modules_bound(root,executor,fixture_fn,plan_type)
    require(snapshot(original)==original_sha,'original fixture mutated after scan')
    return {
        'schema':SCHEMA,'status':STATUS,'grid':[
            {'fabric_slots_per_tick':l,'max_inflight_occurrences':i} for l,i in GRID],
        'source_sha256':before,'original_fixture_sha256':original_sha,
        'same_fixture_before_after_every_run':True,
        'capacity_changes_only_link_fabric_and_transport_inflight':True,
        'cells':rows,'claims_excluded':EXCLUSIONS,
    }


def verify_v0u_reference(report, reference):
    """Anchor TWO fully recomputed native capacity cells to v0u + v0t chain."""
    require(type(report) is dict and report.get('schema')==SCHEMA, 'bad v0v schema')
    require(type(reference) is dict and reference.get('schema')==
            'spk-bv-native-link-pressure-three-arm/v0u' and
            reference.get('status')=='SOURCE_BOUND_LINK_CAPACITY_MODEL_SCAN_ONLY',
            'invalid v0u native reference')
    require(reference.get('v0t_baseline_check',{}).get('status')==
            'PINNED_V0T_AND_V0O_BASELINE_REPLAYED',
            'v0u reference not pinned back to v0t/v0o')
    require(reference.get('same_fixture_before_after_every_run') is True,
            'v0u original fixture mutated or unchecked')
    require(report['original_fixture_sha256']==reference.get('original_fixture_sha256'),
            'native fixture drift')
    require(report['source_sha256']==reference.get('source_sha256'),
            'native source pins changed')
    require(type(reference.get('cells')) is list and len(reference['cells'])==5,
            'invalid reference cell set')
    require(type(report.get('cells')) is list and len(report['cells'])==len(GRID),
            'invalid scan cells')
    for idx in (0,1):
        actual=report['cells'][idx]
        expected=reference['cells'][idx]
        cap=actual['capacity']
        require(cap['fabric_slots_per_tick']==expected['link_capacity']['fabric_slots_per_tick'] and
                cap['directional_link_slots_per_tick']==expected['link_capacity']['link_slots_per_tick'] and
                cap['max_inflight_occurrences']==4,
                'anchor capacity mismatch')
        # Shared SHA includes transport and link plans: complete input anchor.
        require(actual['shared_cell_input_sha256']==expected['shared_cell_input_sha256'],
                'anchor fixture bytes differ')
        for key,_,_ in ARMS:
            a,e=actual['runs'][key],expected['runs'][key]
            for field in ('whole_result_sha256','metrics','last_forward_terminal_tick',
                          'forward_states_sha256', 'forward_emission_payload_multiset_sha256',
                          'forward_terminal_payload_multiset_sha256',
                          'last_feedback_delivery_tick'):
                require(a[field]==e[field],
                        f'native v0u anchor mismatch: {idx}.{key}.{field}')
    return {'status':'TWO_NATIVE_V0U_CAPACITY_CELLS_REPLAYED',
            'anchors':[{'fabric_slots_per_tick':l,'max_inflight_occurrences':4}
                       for l in (1,2)],
            'v0u_v0t_v0o_reference_chain':True,
            'source_hashes_equal':True,'fixture_bytes_equal':True}
