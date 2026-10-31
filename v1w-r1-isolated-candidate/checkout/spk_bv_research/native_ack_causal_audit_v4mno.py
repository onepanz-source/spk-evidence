"""BV v4m-v4o: provenance, causal replay parity, counterfactual limits."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from hashlib import sha256

from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    LiveBVPlanV0e, execute_live_v0e,
)
from spk_bv_research.grant_rank_integration_v3tuv import (
    ARMS, CAPACITIES, NEW_SCHEDULES, POLICIES, QUOTAS,
)
from spk_bv_research.native_ack_shadow_arbiter_v4jkl import (
    STATUS as SHADOW_STATUS, arbitrate_fixed_source, native_service_tokens,
)
from spk_bv_research.native_ack_causal_replay_v4mno import (
    SCHEMA, STATUS, CausalProbeRejected, SyntheticACKRequest, execute_causal_probe,
)
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import snapshot
from search.spk_bv_v0e_live_evidence import fixture

SIGNED_V4JKL_SHA = '2f95569edb1d52bb930395477a3ad4217a04dbf038dc32c3625413f2347c6bff'
VARIANT = 'W4/deadline-only/PE_REASSIGN_CONDITIONAL_MEMORY_GUARD/protect-forward'


def require(ok, reason):
    if not ok:
        raise CausalProbeRejected(reason)


def parity_without_requests(native, replay):
    """Native simulation equality under ZERO synthetic interventions."""
    actual = replay['native']
    timeline = [{k: v for k, v in row.items() if k != 'synthetic_ack_sends'}
                for row in actual['resources']['timeline']]
    resources = {**actual['resources'], 'timeline': timeline}
    return (actual['forward'] == native['forward'] and
            actual['feedback'] == native['feedback'] and
            resources == native['resources'] and
            actual['policy'] == native['policy'] and
            actual['enabled'] == native['enabled'])


def require_resource_conservation(replay):
    """Independent sums over the executed, NOT exogenous-source, timeline."""
    timeline = replay['native']['resources']['timeline']
    forward = replay['native']['forward']
    feedback = replay['native']['feedback']
    ack = replay['synthetic_ack']
    require(len({row['tick'] for row in timeline}) == len(timeline) and
            all(timeline[i]['tick'] == timeline[i-1]['tick'] + 1
                for i in range(1, len(timeline))), 'causal replay clock gap')
    require(sum(t['forward_computations'] for t in timeline) ==
            len(forward['batches']), 'causal replay forward lost work')
    require(sum(t['feedback_sends'] for t in timeline) ==
            len(feedback['link_grants']), 'causal replay BV lost service')
    require(sum(t['synthetic_ack_sends'] for t in timeline) ==
            len(ack['transport_grants']) == len(ack['transport_deliveries']) ==
            ack['requests'], 'causal replay ACK credit gap')
    require(sum(t['pe_service_total'] for t in timeline) ==
            len(forward['batches']) + len(feedback['link_grants']) +
            len(ack['transport_grants']), 'causal replay PE conservation')
    require(sum(t['link_total'] for t in timeline) ==
            len(forward['link_grants']) + len(feedback['link_grants']) +
            len(ack['transport_grants']), 'causal replay link conservation')
    require(sum(t['memory_total'] for t in timeline) ==
            replay['native']['resources']['forward_reserved_memory_units'] +
            2 * len(feedback['link_grants']) + 2 * len(ack['transport_grants']),
            'causal replay O/E memory conservation')
    require(all(g['delivered_at'] > g['tick'] >= g['ready']
                for g in ack['transport_grants']) and
            all(not d['actor_credit_applied'] for d in ack['transport_deliveries']) and
            ack['applied_actor_credits'] == 0 and
            ack['owner_ACK_FIFOs_decremented'] == 0,
            'synthetic transport misreported as actor ACK credit')


def evaluate(v3, raw3, shadow, raw_shadow, *, fixture_fn=fixture,
             native_executor=execute_live_v0e, derived_executor=execute_causal_probe):
    require(type(v3) is dict and type(raw3) is bytes and canon(v3) == raw3 and
            type(shadow) is dict and type(raw_shadow) is bytes and
            canon(shadow) == raw_shadow and
            sha256(raw_shadow).hexdigest() == SIGNED_V4JKL_SHA and
            shadow.get('status') == SHADOW_STATUS and
            shadow.get('signed_v3tuv_sha256') == sha256(raw3).hexdigest() and
            shadow.get('actual_native_scheduler_rearbitration_implemented') is False and
            shadow.get('native_actor_learning_implemented') is False,
            'v4m unsigned/forged predecessor or incorrect semantics')
    contexts = shadow['source_contexts']
    require(type(contexts) is list and len(contexts) == 72 and
            type(v3.get('source_matrix')) is list and
            len(v3['source_matrix']) == len(NEW_SCHEDULES) == 3,
            'v4m source/actor matrix size drift')
    summaries = []
    total = Counter()
    first_drift = None
    first_fingerprint = None
    context_index = 0
    for source, (schedule, ticks) in zip(v3['source_matrix'], NEW_SCHEDULES):
        require(source['schedule'] == schedule and
                source['source_external_ticks'] == list(ticks),
                'v4m source schedule identity drift')
        case, fabric, plans = fixture_fn(ticks=ticks)
        owners = {p.node_id: p.pe_id for p in fabric.placement}
        require(owners.get('A') == 'PE0' and owners.get('B') == 'PE1',
                'v4m synthetic sender/receiver PE ownership drift')
        for mode, (name, enabled, priority) in zip(source['modes'], ARMS):
            require(mode['mode'] == name, 'v4m source mode drift')
            for cap_record, cap in zip(mode['capacities'], CAPACITIES):
                require(cap_record['native_PE_capacity'] == cap,
                        'v4m source capacity drift')
                pplan = replace(plans[1], fabric_slots_per_tick=cap)
                bv = LiveBVPlanV0e(enabled=enabled, priority=priority)
                native = native_executor(case, fabric, plans[0], pplan,
                                         plans[2], plans[3], bv)
                require(snapshot(native) == cap_record['original_native_sha256'],
                        'v4m unsigned changed original native execution')
                no_op = derived_executor(case, fabric, plans[0], pplan,
                                         plans[2], plans[3], bv, ())
                require(parity_without_requests(native, no_op),
                        'v4m ZERO-intervention frozen native parity failed')
                require_resource_conservation(no_op)
                total['original_native_replays'] += 1
                operations = native_service_tokens(native, owners)
                mem = plans[2]
                shared = {
                    'global_cap': cap, 'owner_cap': dict(pplan.pe_slots)['PE0'],
                    'owner_memory_cap': dict(mem.pe_slots)['PE0'],
                    'total_memory_cap': mem.fabric_slots_per_tick,
                    'O_cap': dict(mem.domain_slots)['O'],
                    'E_cap': dict(mem.domain_slots)['E'],
                }
                for policy in POLICIES:
                    for quota in QUOTAS:
                        source_context = contexts[context_index]
                        context_index += 1
                        require(all(source_context[k] == value for k, value in (
                            ('schedule', schedule), ('mode', name),
                            ('native_global_PE_capacity', cap),
                            ('policy', policy), ('ACK_quota', quota))),
                            'v4m signed source context order/custody drift')
                        row = source_context['variants'][VARIANT]
                        source_rows = cap_record['derived_policies'][policy][str(quota)][
                            'rank_audit']['per_tick_fifo_prefix']
                        recalculated = arbitrate_fixed_source(
                            source_rows, native['resources']['timeline'], operations,
                            window=4, strategy='deadline-only',
                            allow_PE_reassign=True, donor_preference='protect-forward',
                            **shared)
                        require(recalculated == row,
                                'v4m predecessor ledger not reproducible from signed native')
                        requests = tuple(SyntheticACKRequest(
                            f'exo-{i:03d}', event['tick'])
                            for i, event in enumerate(row['reservation_ledger'], 1))
                        require(all(event['source_ACK_payload_delivered'] is False
                                    for event in row['reservation_ledger']),
                                'v4m counterfeit existing actor ACK delivery')
                        replay = derived_executor(case, fabric, plans[0], pplan,
                                                  plans[2], plans[3], bv, requests)
                        require_resource_conservation(replay)
                        grants = replay['synthetic_ack']['transport_grants']
                        require(len(grants) == len(requests) and
                                [g['identity'] for g in grants] ==
                                [r.identity for r in requests],
                                'v4m synthetic request FIFO loss or reorder')
                        own = replay['native']
                        native_forward_same = own['forward'] == native['forward']
                        native_feedback_same = own['feedback'] == native['feedback']
                        terminal_same = own['forward']['terminal'] == native['forward']['terminal']
                        output_state_same = own['forward']['states'] == native['forward']['states']
                        horizon_extension = (len(own['resources']['timeline']) -
                                             len(native['resources']['timeline']))
                        require(horizon_extension >= 0 and
                                len(replay['synthetic_ack']['transport_deliveries']) ==
                                len(requests), 'v4m native causal reexecution incomplete')
                        datum = {
                            'schedule': schedule, 'mode': name,
                            'native_global_PE_capacity': cap,
                            'policy': policy, 'ACK_quota': quota,
                            'source_shadow_debt_tokens': len(row['native_service_debt_ledger']),
                            'exogenous_ACK_requests': len(requests),
                            'simulated_ACK_link_grants_and_deliveries': len(grants),
                            'simulated_ACK_max_wait_ticks': max((g['wait'] for g in grants), default=0),
                            'replayed_native_forward_exact_parity': native_forward_same,
                            'replayed_native_BV_exact_parity': native_feedback_same,
                            'replayed_terminal_exact_parity': terminal_same,
                            'replayed_final_state_exact_parity': output_state_same,
                            'native_completion_horizon_extension_ticks': horizon_extension,
                            'native_forward_processed_events_delta':
                                own['forward']['processed_events'] - native['forward']['processed_events'],
                            'native_forward_processed_batches_delta':
                                own['forward']['processed_batches'] - native['forward']['processed_batches'],
                        }
                        summaries.append(datum)
                        total['derived_scenarios'] += 1
                        total['exogenous_requests'] += len(requests)
                        total['simulated_ack_deliveries'] += len(grants)
                        total['source_shadow_debt_tokens'] += len(row['native_service_debt_ledger'])
                        total['native_forward_changed_scenarios'] += int(not native_forward_same)
                        total['native_BV_changed_scenarios'] += int(not native_feedback_same)
                        total['terminal_changed_scenarios'] += int(not terminal_same)
                        total['final_state_changed_scenarios'] += int(not output_state_same)
                        total['horizon_extended_scenarios'] += int(horizon_extension > 0)
                        if first_drift is None and (not native_forward_same or
                                                    not native_feedback_same):
                            first_drift = datum
                        if first_fingerprint is None and requests:
                            first_fingerprint = {
                                'source_original_native_sha256': snapshot(native),
                                'derived_replay_sha256': sha256(canon(replay)).hexdigest(),
                                'request_count': len(requests),
                                'first_exogenous_ACK_request_tick': requests[0].tick,
                                'first_actual_ACK_grant_tick': grants[0]['tick'],
                            }
    require(context_index == total['derived_scenarios'] == 72 and
            total['original_native_replays'] == 18 and
            total['exogenous_requests'] == total['simulated_ack_deliveries'] == 399 and
            total['source_shadow_debt_tokens'] == 291 and
            total['native_forward_changed_scenarios'] > 0 and
            total['native_BV_changed_scenarios'] > 0,
            'v4m finite matrix/causal effects not established')
    return {
        'schema': SCHEMA, 'status': STATUS,
        'signed_v3tuv_sha256': sha256(raw3).hexdigest(),
        'signed_v4jkl_sha256': sha256(raw_shadow).hexdigest(),
        'scenario': VARIANT,
        'exogenous_request_model': {
            'issuer': 'SIGNED_SHADOW_RESERVATION_TICKS_NOT_CHANGED_ACTOR_READINESS',
            'sender_PE': 'PE0', 'receiver_PE': 'PE1',
            'service_order': 'SYNTHETIC_ACK_AHEAD_OF_NATIVE_FORWARD_AND_BV',
            'owner_actor_credit_applied': False,
            'native_forward_BV_reexecuted': True,
        },
        'totals': dict(sorted(total.items())),
        'first_changed_native_example': first_drift,
        'first_signed_reexecution_fingerprint': first_fingerprint,
        'source_derived_contexts': summaries,
        'claims_excluded': [
            'synthetic ACK requests are fixed exogenous shadow ticks, not actual actor intents',
            'actual actor ACK FIFO credit, receiver evidence and learning are not executed',
            'old static donor identities are not necessarily the work delayed by the new scheduler',
            '291 prior donor tokens are not certified paid or reexecuted one-for-one',
            'no unconditional W4 deadline or native scheduler/architecture adoption',
            'the transport cost is abstract, not energy, hardware or N-node runtime',
        ],
        'native_v0e_modified': False,
        'native_Architecture_v1_modified': False,
        'real_actor_ACK_credit_applied': False,
        'native_scheduler_policy_adopted': False,
        'next_gate': 'DYNAMIC_ACTOR_REQUEST_PROVENANCE_AND_RECEIVER_CREDIT_REEXECUTION',
    }
