"""V5-T2e: source-executed *abstract* BV resource envelope for a logical island.

Do NOT reinterpret v0e terminal-channel assessment as task-semantic feedback.
The T2c C-demand/closure receipt is separate, shadow-only, and still uncharged.
Frozen A1b/A3d/BV-v0e sources are imported unchanged.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import replace

from spk_architecture_v1.pe_fabric_v1a import plan_v1a
from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
from spk_architecture_v1.causal_memory_v1c import uniform_causal_memory_plan_v1c
from spk_architecture_v1.causal_transport_v1d import CausalLinkPlanV1d
from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    LiveBVPlanV0e, execute_live_v0e,
)
from spk_v5_research.island_objective_v5t1 import CANDIDATES, digest
from spk_v5_research.island_endogenous_demand_v5t2c import (
    DemandEpisode, generate_corpus, make_case, observe_closed_episode,
)

SCHEMA = 'spk-v5-t2e-bv-abstract-resource-bridge/research-v0'
MODES = ('disabled', 'forward_first', 'feedback_first', 'closure_only')


def source_plan(record: DemandEpisode, candidate: str):
    """Finite admitted original v0e plans; topology is a research fixture only."""
    case = make_case(record, candidate)
    fabric = plan_v1a(case, 'spread')
    return case, fabric, (
        TransportPlanV1a(0, 16),
        uniform_causal_service_plan_v1b(fabric, pe_slots=3, fabric_slots_per_tick=4),
        uniform_causal_memory_plan_v1c(fabric, pe_slots=256, domain_slots=256,
                                       fabric_slots_per_tick=768),
        CausalLinkPlanV1d(link_slots_per_tick=1, fabric_slots_per_tick=1,
                          max_outbox_per_pe=128, max_link_span_ticks=256),
    )


def source_execution(record: DemandEpisode, candidate: str, mode: str):
    if (type(record) is not DemandEpisode or type(record.demand) is not bool
            or candidate not in CANDIDATES or mode not in MODES):
        raise ValueError('inadmissible V5-T2e source measurement')
    case, fabric, plans = source_plan(record, candidate)
    return execute_live_v0e(case, fabric, *plans, LiveBVPlanV0e(
        enabled=mode != 'disabled',
        priority='feedback-first' if mode in ('feedback_first', 'closure_only')
                 else 'forward-first',
        assessor='C', terminal_channel=9 if mode == 'closure_only' else 7,
        max_ticks=256))


def audit_resource_execution(record: DemandEpisode, candidate: str,
                             mode: str, result: dict) -> dict:
    """Derive costs exclusively from v0e's charged grants/timeline.

    Do not consume a caller-provided cost total or fabricate closed semantic ACKs.
    """
    if type(result) is not dict or result.get('schema') != 'spk-bv-live-dual-event-scheduler/v0e':
        raise ValueError('not a source-executed frozen v0e result')
    if result.get('enabled') != (mode != 'disabled'):
        raise ValueError('mode/source-enabled mismatch')
    resources, feedback, forward = (result[x] for x in ('resources', 'feedback', 'forward'))
    timeline = resources['timeline']
    if not timeline or len({x['tick'] for x in timeline}) != len(timeline):
        raise ValueError('non-unique source resource timeline')
    fg, bg = forward['link_grants'], feedback['link_grants']
    bv = len(bg)
    if (resources['forward_link_grants'] != len(fg) or
            resources['bv_link_grants'] != bv or
            resources['bv_service_units'] != bv or
            resources['bv_memory_units'] != 2*bv or
            sum(x['feedback_sends'] for x in timeline) != bv or
            sum(x['pe_service_total'] for x in timeline) < bv or
            sum(x['link_total'] for x in timeline) != len(fg)+bv):
        raise ValueError('BV service/memory/link budget conservation failure')
    ticks = {row['tick']:row for row in timeline}
    if any(t['link_total'] > 1 or t['pe_service_total'] > 4 or
           t['memory_total'] > 768 for t in timeline):
        raise ValueError('shared capacity exceeded')
    if any(g['tick'] not in ticks or g['delivered_at'] <= g['tick']
           for g in fg + bg):
        raise ValueError('grant violates causal timeline')
    closure = [x for x in forward['terminal'] if x['node_id']=='C' and x['channel']==9]
    if len(closure) != 1:
        raise ValueError('C failed to close exactly once')
    if mode == 'closure_only' and (len(feedback['assessments']) != 1 or bv):
        raise ValueError('closure-only without ancestry cannot mint feedback')
    if mode == 'disabled' and (feedback['assessments'] or bv):
        raise ValueError('disabled BV minted reverse service')
    if candidate == 'silent' and bv:
        raise ValueError('a silent decision created a provenance-free reverse ACK')
    return {
        'forward_grants':len(fg),
        'feedback_grants':bv,
        'feedback_deliveries':len(feedback['deliveries']),
        'abstract_PE_service_units':bv,
        'abstract_OE_memory_units':2*bv,
        'abstract_reverse_link_grants':bv,
        'total_link_grants':len(fg)+bv,
        'total_resource_ticks':len(timeline),
        'closure_tick':closure[0]['timestamp'],
        'forward_at_C_ticks':[x['timestamp'] for x in forward['terminal']
                              if x['node_id']=='C' and x['channel']==7],
        'terminal_sha256':digest(forward['terminal']),
        'resource_timeline_sha256':digest(timeline),
        'max_link_per_tick':max(row['link_total'] for row in timeline),
        'assessment_count':len(feedback['assessments']),
    }



def verify_source_replay(record: DemandEpisode, candidate: str,
                         mode: str, claimed: dict) -> None:
    """A rehashed invented ledger is not executable source evidence."""
    if type(claimed) is not dict or digest(claimed) != digest(source_execution(record,candidate,mode)):
        raise ValueError('source-owned v0e replay mismatch')


def benchmark_cases() -> tuple[tuple[DemandEpisode, str], ...]:
    """All seven predeclared templates x two C-demand outcomes x three arms."""
    source = generate_corpus(blocks=1, seed=37217, regime='aligned', train=False)
    if tuple(x.template_id for x in source) != tuple(range(7)):
        raise AssertionError('unexpected inherited source templates')
    return tuple((replace(r, demand=d), c)
                 for r in source for d in (False, True) for c in CANDIDATES)


def run_t2e() -> dict:
    cells, totals = [], {name:Counter() for name in MODES}
    changed, wrong_time = Counter(), Counter()
    for record, candidate in benchmark_cases():
        # The A1b task judgment is shadow-only. It MUST NOT become a v0e ACK.
        actual = observe_closed_episode(record, candidate)
        result = {}
        raw = {}
        for mode in MODES:
            execution = source_execution(record, candidate, mode)
            source_audit = audit_resource_execution(record, candidate, mode, execution)
            raw[mode] = execution
            result[mode] = source_audit
            totals[mode].update({key:source_audit[key] for key in (
                'forward_grants','feedback_grants','abstract_PE_service_units',
                'abstract_OE_memory_units','total_link_grants')})
            totals[mode]['feedback_bearing_cells'] += int(source_audit['feedback_grants']>0)
            totals[mode]['closure_count'] += 1
        for mode in MODES[1:]:
            if raw[mode]['forward']['terminal'] != raw['disabled']['forward']['terminal']:
                changed[mode] += 1
            if raw[mode]['forward']['batches'] != raw['disabled']['forward']['batches']:
                wrong_time[mode] += 1
        cells.append({
            'template_id':record.template_id, 'world_demand_synthetic':record.demand,
            'candidate':candidate,
            'A1b_shadow_semantic_verdict':actual.verdict,
            'A1b_shadow_local_reward':actual.local_reward,
            'A1b_shadow_forward_C_ticks':list(actual.c_forward_ticks),
            'source_v0e_modes':result,
        })
    return {
        'schema':SCHEMA,
        'status':'T2E_ACTUAL_V0E_ABSTRACT_COSTS_PASS_SEMANTIC_REVERSE_CHANNEL_BLOCKED',
        'cells':len(cells),
        'coverage':'7 temporal templates x 2 exogenous synthetic demand bits x 3 candidate programs',
        'observed_engine':'unchanged research BV v0e shared-clock scheduler + unchanged frozen A1b C-closure observer',
        'source_synthetic_input_sha256':digest([(c['template_id'],c['world_demand_synthetic'],c['candidate']) for c in cells]),
        'modes':{mode:dict(sorted(totals[mode].items())) for mode in MODES},
        'changed_terminal_cells_vs_v0e_disabled':dict(sorted(changed.items())),
        'changed_batch_cells_vs_v0e_disabled':dict(sorted(wrong_time.items())),
        'cell_evidence':cells,
        'semantic_reverse_credit_proven':False,
        'charged_semantic_rewards':0,
        'native_learning':False,
        'architecture_modified':False,
        'inference_boundary':[
            'v0e terminal-7 assessments are causal echo judgments from a C forward emission, NOT task-semantic reward',
            'v0e closure at C channel 9 has no upstream spike ancestry and cannot transmit a silent-action negative judgment',
            'A1b shadow C-demand reward is NOT transported through v0e and its reverse consumer costs are NOT paid',
            'Source charges are abstract v0e PE/OE memory/link grants, NOT physical energy or a production guarantee',
            'A1b baseline and v0e-disabled use distinct schedulers; no automatic all-input behavioral parity',
            'Shared-resource arbitration may change C timing and coalescing even when candidate and input are identical',
            'All environmental bits are experimenter-generated; NO real-world oracle, independent blind data, or T3 go',
        ],
    }
