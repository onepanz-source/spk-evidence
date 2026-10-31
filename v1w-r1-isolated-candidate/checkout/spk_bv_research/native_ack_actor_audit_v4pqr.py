"""v4p-v4r finite signed-source audit, causal parity and resource invariants."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from hashlib import sha256

from search.spk_bv_v0e_live_evidence import fixture
from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    LiveBVPlanV0e, execute_live_v0e,
)
from spk_bv_research.grant_rank_integration_v3tuv import (
    ARMS, CAPACITIES, NEW_SCHEDULES,
)
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import snapshot
from spk_bv_research.native_ack_actor_loop_v4pqr import (
    SCHEMA, STATUS, CausalProbeRejected, _sha_receipt, execute_endogenous_probe,
)

SIGNED_V3TUV_SHA = 'f783be9952613aa98eafef59d24c19eb64ccc09d29265017eabb675fe0155827'
SIGNED_V4MNO_SHA = '0030c7bd9c84c022b3eddfadce4ae590f919186c5ee76a228cf57870b7f55721'
INTERVENTIONS = (
    ('normal', True, 256),
    ('feedback_disabled', False, 256),
    ('zero_actor_credit', True, 0),
    ('narrow_actor_credit', True, 1),
)


def require(ok, why):
    if not ok:
        raise CausalProbeRejected(why)


def conservation(replay):
    native = replay['native']
    rows = native['resources']['timeline']
    forward = native['forward']
    back = native['feedback']
    ack = replay['derived_actor_ack']
    judgments = replay['derived_actor']['judgments']
    receipts = replay['derived_actor']['applied_receipts']
    reqs = ack['requests']
    grants = ack['transport_grants']
    deliveries = ack['transport_deliveries']
    require(len(rows) == len({x['tick'] for x in rows}) and
            all(rows[i]['tick'] == rows[i-1]['tick'] + 1
                for i in range(1, len(rows))), 'v4p causal native tick gap')
    require(len(grants) == len(deliveries) == len(judgments) == reqs and
            sum(x['actor_ack_sends'] for x in rows) == reqs and
            sum(x['forward_computations'] for x in rows) == len(forward['batches']) and
            sum(x['feedback_sends'] for x in rows) == len(back['link_grants']) and
            sum(x['pe_service_total'] for x in rows) ==
              len(forward['batches']) + len(back['link_grants']) + reqs and
            sum(x['link_total'] for x in rows) ==
              len(forward['link_grants']) + len(back['link_grants']) + reqs and
            sum(x['memory_total'] for x in rows) ==
              native['resources']['forward_reserved_memory_units'] +
              2 * len(back['link_grants']) + 2 * reqs,
            'v4p actual PE/link/memory service conservation failed')
    require([r['identity'] for r in grants] ==
            [r['identity'] for r in deliveries] ==
            [j['identity'] for j in judgments] and
            all(g['tick'] >= g['ready'] > j['created_tick'] >= j['ingress_tick'] >
                j['emitted_tick'] and g['delivered_at'] > g['tick'] and
                g['source_pe'] == j['source_pe'] and
                g['target_pe'] == j['target_pe'] and
                d['tick'] == g['delivered_at'] and
                d['target_pe'] == j['target_pe']
                for g, d, j in zip(grants, deliveries, judgments)),
            'v4p generated judgment/request/grant/delivery custody diverged')
    occurrences = {o['id']: o for o in forward['occurrences']}
    batches = {(b['node'], b['tick']): b for b in forward['batches']}
    require(all(j['source_emission'] in occurrences and
                occurrences[j['source_emission']]['source'] == j['recipient'] and
                occurrences[j['source_emission']]['target'] == j['issuer'] and
                occurrences[j['source_emission']]['delivered_at'] == j['ingress_tick'] and
                j['source_emission'] in batches[(j['issuer'],j['created_tick'])]['parents'] and
                j['response'] ==
                  (1 if batches[(j['issuer'],j['created_tick'])]['outputs'] else -1)
                for j in judgments),
            'v4p actor semantic sign is not from actual recomputed native output')
    require(len(receipts) == sum(bool(d['actor_credit_applied']) for d in deliveries) ==
            ack['applied_actor_credits'] == ack['owner_ACK_FIFOs_decremented'] and
            replay['native_actor_credit_applied'] is False and
            replay['native_learning_implemented'] is False,
            'v4p actor applied-credit is missing or misattributed to native learning')
    roots = {actor:'0'*64 for actor in replay['derived_actor']['applied_credit_by_actor']}
    balances = {actor:0 for actor in roots}
    seqs = {actor:0 for actor in roots}
    acknowledged = set()
    by_identity = {j['identity']: j for j in judgments}
    for receipt in receipts:
        actor = receipt['actor']
        require(receipt['judgment_id'] in by_identity,
                'v4p actor receipt references nonexistent signed judgment')
        j = by_identity[receipt['judgment_id']]
        prior = receipt.copy()
        digest = prior.pop('chain_digest')
        require(receipt['judgment_id'] not in acknowledged and
                digest == _sha_receipt(prior) and
                receipt['chain_prev'] == roots[actor] and
                receipt['credit_before'] == balances[actor] and
                receipt['credit_after'] == balances[actor] + j['response'] and
                receipt['seq'] == seqs[actor] + 1 and
                receipt['actor'] == j['recipient'] and
                receipt['owner_pe'] == j['target_pe'] and
                abs(receipt['credit_after']) <=
                   replay['derived_actor']['max_abs_actor_credit'],
                'v4p replayed, forged or reordered actor consumer receipt')
        acknowledged.add(receipt['judgment_id'])
        roots[actor] = digest
        balances[actor] = receipt['credit_after']
        seqs[actor] += 1
    require(roots == replay['derived_actor']['receipt_roots'] and
            balances == replay['derived_actor']['applied_credit_by_actor'],
            'v4p actor credit chain root does not close')


def no_feedback_exact_native_parity(native, disabled):
    own = disabled['native']
    rows = [{k:v for k,v in row.items() if k != 'actor_ack_sends'}
            for row in own['resources']['timeline']]
    return (own['forward'] == native['forward'] and
            own['feedback'] == native['feedback'] and
            {**own['resources'], 'timeline': rows} == native['resources'] and
            disabled['derived_actor_ack']['requests'] == 0 and
            not disabled['derived_actor']['applied_receipts'])


def evaluate(v3, raw3, v4m, raw4m, *, fixture_fn=fixture,
             native_executor=execute_live_v0e,
             derived_executor=execute_endogenous_probe):
    require(type(v3) is dict and type(raw3) is bytes and
            canon(v3) == raw3 and
            sha256(raw3).hexdigest() == SIGNED_V3TUV_SHA and
            type(v4m) is dict and type(raw4m) is bytes and
            canon(v4m) == raw4m and
            sha256(raw4m).hexdigest() == SIGNED_V4MNO_SHA and
            v4m['signed_v3tuv_sha256'] == SIGNED_V3TUV_SHA and
            v4m['totals']['original_native_replays'] == 18 and
            v4m['totals']['derived_scenarios'] == 72 and
            v4m['real_actor_ACK_credit_applied'] is False and
            v4m['native_scheduler_policy_adopted'] is False,
            'v4p predecessor or canonical SHA drift')
    totals = Counter()
    scenarios = []
    for source, (schedule, ticks) in zip(v3['source_matrix'], NEW_SCHEDULES):
        require(source['schedule'] == schedule and
                source['source_external_ticks'] == list(ticks),
                'v4p native signed source schedule mismatch')
        case, fabric, plans = fixture_fn(ticks=ticks)
        for mode, (name, enabled, priority) in zip(source['modes'], ARMS):
            require(mode['mode'] == name, 'v4p source BV mode drift')
            for capacity, cap in zip(mode['capacities'], CAPACITIES):
                require(capacity['native_PE_capacity'] == cap,
                        'v4p source global PE cap drift')
                pplan = replace(plans[1], fabric_slots_per_tick=cap)
                bv = LiveBVPlanV0e(enabled=enabled, priority=priority)
                native = native_executor(case, fabric, plans[0], pplan,
                                         plans[2], plans[3], bv)
                require(snapshot(native) == capacity['original_native_sha256'],
                        'v4p original signed native execution changed')
                totals['original_native_replays'] += 1
                for variant, feedback, credit_cap in INTERVENTIONS:
                    result = derived_executor(case, fabric, plans[0], pplan,
                                              plans[2], plans[3], bv,
                                              feedback=feedback,
                                              max_abs_actor_credit=credit_cap)
                    conservation(result)
                    if variant == 'feedback_disabled':
                        require(no_feedback_exact_native_parity(native, result),
                                'v4p null intervention native parity failed')
                        totals['native_null_exact_parity'] += 1
                    ack = result['derived_actor_ack']
                    applied = result['derived_actor']['applied_receipts']
                    require(ack['requests'] == (16 if feedback else 0) and
                            (variant != 'zero_actor_credit' or not applied) and
                            (variant != 'normal' or len(applied) == ack['requests']) and
                            all(j['source_emission'] for j in
                                result['derived_actor']['judgments']),
                            'v4p actor source, denial or completion mismatch')
                    totals['derived_scenarios'] += 1
                    totals['originated_judgments'] += ack['requests']
                    totals['PE_link_charged_ACK_deliveries'] += len(ack['transport_deliveries'])
                    totals['derived_actor_credit_applied'] += len(applied)
                    totals['actor_credit_policy_denials'] += sum(
                        d.get('actor_credit_denied_by_policy') is True
                        for d in ack['transport_deliveries'])
                    totals['native_forward_changed_scenarios'] += int(
                        result['native']['forward'] != native['forward'])
                    scenarios.append({
                        'schedule': schedule, 'mode': name,
                        'native_global_PE_capacity': cap, 'variant': variant,
                        'originated_judgments': ack['requests'],
                        'delivered_judgments': len(ack['transport_deliveries']),
                        'derived_actor_credits': len(applied),
                        'native_forward_equal': result['native']['forward'] == native['forward'],
                        'native_feedback_equal': result['native']['feedback'] == native['feedback'],
                        'final_native_states_equal': result['native']['forward']['states'] ==
                            native['forward']['states'],
                    })
    require(len(v3['source_matrix']) == 3 and
            totals['original_native_replays'] == 18 and
            totals['derived_scenarios'] == 72 and
            totals['native_null_exact_parity'] == 18 and
            totals['originated_judgments'] == totals['PE_link_charged_ACK_deliveries'] ==
                18*3*16 and
            totals['derived_actor_credit_applied'] > 0 and
            totals['actor_credit_policy_denials'] > 0 and
            totals['native_forward_changed_scenarios'] > 0,
            'v4p finite source matrix counterfactual is incomplete')
    return {
        'schema': SCHEMA, 'status': STATUS,
        'signed_v3tuv_sha256': sha256(raw3).hexdigest(),
        'signed_v4mno_sha256': sha256(raw4m).hexdigest(),
        'native_scheduler_source': 'PINNED_V4MNO_REEXECUTION_FORK',
        'semantic_source': 'RECOMPUTED_RECEIVER_BATCH_OUTPUT_POSITIVE_IF_NONEMPTY',
        'feedback_transport': 'SHARED_PE_O_E_MEMORY_DIRECTIONAL_LINK_INFLIGHT',
        'actor_credit_target': 'DERIVED_ACTOR_LOCAL_REGISTER_ONLY',
        'interventions': [name for name, _, _ in INTERVENTIONS],
        'totals': dict(sorted(totals.items())),
        'scenarios': scenarios,
        'native_v0e_modified': False,
        'native_Architecture_v1_modified': False,
        'native_operator_updates': 0,
        'native_learning_implemented': False,
        'native_actor_ACK_consumer_implemented': False,
        'claims_excluded': [
            'the derived receiver decision (+1 output, -1 no output) is a research policy, not a universal error signal',
            'derived actor credit is not frozen-native actor/learner admission or weight update',
            'native feedback and actor ACK are independently modeled controls and may compete for resources',
            'credit register application reuses charged ACK transport grant; extra computation cost is not established',
            'no network authentication; a local receipt hash chain does not certify remote identity',
            'zero-capacity actor policy denial is not a negative judgment or delivery loss',
            'three-actor fixed workload and capacity matrix, no arbitrary topology or universal deadline',
            'no architecture adoption, PE remapping, hardware/energy measurement or source identity weights',
        ],
        'next_gate': 'FROZEN_NATIVE_ACTOR_CONSUMER_ADMISSION_AND_LEARNING_AUTHORITY_NOT_IMPLEMENTED',
    }
