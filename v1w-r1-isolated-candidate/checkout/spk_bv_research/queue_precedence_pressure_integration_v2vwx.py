"""BV v2v–v2x cumulative ACK/consumer source-backed queue-policy evidence.

The finite bounded-turn policy is audited, but the source-pinned workloads
do NOT witness two consecutive contested consumer turns. Never claim a
universal ACK-liveness theorem or frozen-native scheduling intervention.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import (
    require, snapshot, source_pins, runtime_modules_bound,
)
from spk_bv_research.coincident_admission_discrimination_v2e import (
    RECIPES, build_workload,
)
from spk_bv_research.link_pressure_v0u import ARMS, _arm
from spk_bv_research.actor_priority_contention_integration_v2m import REGIMES, _payload
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources
from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver, read_pinned_source,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import ReceiverPortV2h
from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import ActorCreditPlanV2l
from spk_backvalidation_v2.derived_actor_control_service_v2j import ShadowServicePlanV2j
from spk_backvalidation_v2.derived_causal_admission_v2o import CausalAdmissionPlanV2o
from spk_backvalidation_v2.derived_concurrent_consumer_v2s import ConcurrentConsumerPlan
from spk_backvalidation_v2.derived_actor_queue_fairness_v2v import (
    POLICIES, ActorQueuePlanV2v, DerivedActorQueueFairnessV2v,
    derive_queue_fairness_executor,
)

SCHEMA = 'spk-bv-pinned-two-queue-precedence-and-bounded-window-discriminator/v2v-v2x'
STATUS = 'DERIVED_TWO_QUEUE_PRIORITY_CAUSAL_DISCRIMINATION_NO_NATIVE_LIVENESS_CONTRACT'
CONTRACT = 'V2V_V2X_SIGNED_V2STU_PREDECESSOR_ONLY'
PREDECESSOR_SHA = '418f8154b25ed78bcbb5dc6ba5f8a0968dc107425d43c2e38c71ba2485b11975'
GUARDS = (('strict_native_ready', True, True),
          ('actor_first_null_guard', False, False))
INTERVENTIONS = ('pre_consumer_zero', 'credit_zero', 'transport_loss')
EXCLUSIONS = (
    'two_queue_priority_changes_only_separately_compiled_derived_schedule',
    'source_fifo_ACK_provenance_and_independent_consumer_charge_are_distinct',
    'two_tick_receiver_transport_delay_is_an_explicit_research_intervention',
    'one_global_ACK_service_per_tick_is_source_capped_and_replayable',
    'bounded_turns_policy_has_no_multi_consecutive_contention_witness_in_matrix',
    'finite_queue_preference_does_not_prove_universal_eventual_ACK_service',
    'zero_consumer_cannot_turn_lost_or_withheld_judgment_into_negative_credit',
    'strict_native_ready_full_parity_claim_only_for_15_by_3_by_2_matrix',
    'no_frozen_native_actor_intake_learning_priority_or_cross_node_authenticity',
    'no_hardware_calibration_or_general_network_quorum',
)


def validate_v2stu(prev, raw):
    require(type(prev) is dict and type(raw) is bytes and canon(prev) == raw and
            sha256(raw).hexdigest() == PREDECESSOR_SHA,
            'v2v-v2x signed v2stu predecessor canonical/SHA drift')
    require(prev.get('schema') ==
            'spk-bv-cumulative-source-pinned-concurrent-consumer-arbiter/v2s-v2u' and
            prev.get('status') ==
            'DERIVED_TRUE_PRE_FORWARD_PAID_CONSUMER_CAUSAL_ARBITRATION_NATIVE_BLOCKED',
            'v2v-v2x invalid v2stu signed predecessor semantic identity')
    # Explicit predecessor identities and excluded native claims matter more
    # than a favourable empirical matrix cell.
    require(prev.get('reference_v2r_sha256') ==
            '731050ab7dc675b073afa9625b1cd378a9a4b7289e51d7f61078af294ba9f279'
            and prev.get('new_native_runs') == 90 and
            prev.get('new_derived_three_way_guard_runs') == 360 and
            prev.get('new_derived_causal_intervention_runs') == 180 and
            prev.get('causal_consumer_forward_witness_cells') == 45 and
            prev.get('independent_derived_pre_forward_actor_consumer_proven') is True and
            prev.get('frozen_native_concurrent_three_way_arbiter_proven') is False and
            prev.get('frozen_native_actor_learning_contract_proven') is False and
            prev.get('native_operator_updates') == 0 and
            prev.get('next_gate') ==
                'BLOCKED_EXPLICIT_FROZEN_NATIVE_ACTOR_SERVICE_AND_LEARNING_CONTRACT',
            'v2v-v2x signed source contract or native exclusion drift')
    totals = prev.get('three_way_paid_resource_totals') or {}
    require(all(totals.get(regime, {}).get('strict_native_ready', {}).get(
                    'full_native_equal') == 45 and
                totals[regime]['strict_native_ready']['ACKs'] == 156 and
                totals[regime]['strict_native_ready']['consumer_paid'] == 156
                for regime, _ in REGIMES),
            'v2v-v2x predecessor strict resource/native replay incomplete')
    rows = prev.get('paired_native_matrix')
    require(type(rows) is list and len(rows) == len(RECIPES),
            'v2v-v2x signed organic 15-workload proof missing')
    for (label, recipe), row in zip(RECIPES, rows):
        require(row.get('label') == label and
                row.get('recipe') == [list(x) for x in recipe] and
                [mode.get('mode') for mode in row.get('modes', [])] ==
                    [name for name, _, _ in ARMS],
                'v2v-v2x original signed workload order drift')
        for mode in row['modes']:
            for regime, capacity in REGIMES:
                cell = mode.get('capacities', {}).get(regime, {})
                require(cell.get('capacity') == capacity and
                        len(cell.get('signed_v2r_native_sha256', '')) == 64 and
                        cell.get('guard_modes', {}).get('strict_native_ready', {}).get(
                            'full_native_equal') is True,
                        'v2v-v2x signed native/control 90-cell matrix incomplete')
    return True


def _derived(source, native_executor, plan_type, altered, fabric, plans,
             enabled, priority, digest, data, *, label, policy, forward, bv,
             intervention='normal'):
    opts = {'latency': 2}
    consumer_plan = ConcurrentConsumerPlan()
    credit_plan = ActorCreditPlanV2l()
    if intervention == 'pre_consumer_zero':
        consumer_plan = replace(consumer_plan, max_per_tick=0)
    elif intervention == 'credit_zero':
        credit_plan = ActorCreditPlanV2l(max_abs_credit=0)
    elif intervention == 'transport_loss':
        opts['accept'] = lambda _: False
    else:
        require(intervention == 'normal', 'v2v-v2x unsupported causal queue intervention')
    port = ReceiverPortV2h(**opts)
    actor = DerivedActorQueueFairnessV2v(
        port, queue_plan=ActorQueuePlanV2v(policy),
        admission_plan=CausalAdmissionPlanV2o(forward, bv),
        service_plan=ShadowServicePlanV2j(max_per_tick=1),
        concurrent_plan=consumer_plan, credit_plan=credit_plan)
    observer = CallsiteObserver()
    executor, _, semantic, resources = derive_queue_fairness_executor(
        source, native_executor, port, actor, observer)
    captured = {}

    def run(*args, **kwargs):
        captured['raw'] = executor(*args, **kwargs)
        captured['projected'] = actor.project_original_native_result(captured['raw'])
        return captured['projected']

    signed = _arm(run, plan_type, altered, fabric, plans,
                  'v2v-v2x-'+label+'-'+intervention, enabled, priority, digest, data)
    summary = actor.summary()
    acks, receipts, rows = (actor.credit_journal(), actor.concurrent_journal(),
                             actor.queue_fairness_probes())
    require(semantic == (('batch', 194), ('clock', 125),
                         ('emission', 217), ('ingress', 136)) and
            resources == (158, 296, 307) and not observer.overflow and
            not observer.sink_failed and observer.counts()['_admit'] == 1 and
            observer.counts()['_admit_plan'] == 1 and
            summary['queue_priority_policy'] == policy and
            summary['max_consecutive_consumer_turns_with_ready_ACK'] == 1 and
            summary['derived_actor_credit_ack_count'] == len(acks) and
            summary['concurrent_paid_applications'] == len(receipts) and
            summary['concurrent_consumer_PE_units'] == len(receipts) and
            summary['concurrent_consumer_memory_units'] == 2*len(receipts) and
            summary['concurrent_pending_acks'] == len(acks)-len(receipts) and
            summary['native_operator_updates'] == 0 and
            summary['absence_certificates'] == 0 and
            summary['frozen_actor_state_changed'] is False and
            len(rows) == summary['native_original_timeline_rows'],
            'v2v-v2x source-budgeted ACK/consumer queue custody drift')
    if intervention == 'normal':
        require(len(acks) == len(receipts),
                'v2v-v2x normal bounded queue service left ACK unconsumed')
    if intervention == 'pre_consumer_zero':
        require(not receipts and summary['concurrent_pending_acks'] == len(acks),
                'v2v-v2x zero consumer emitted resource charges')
    if intervention in ('credit_zero', 'transport_loss'):
        require(not acks and not receipts,
                'v2v-v2x loss or credit cap fabricated actor ACK')
    return signed, summary, acks, receipts, rows, captured, port.summary()


def experiment(prev, raw, *, root: Path, fixture_fn, native_executor, plan_type):
    validate_v2stu(prev, raw)
    root = root.resolve(strict=True)
    before_pins = source_pins(root)
    before_arch = read_pinned_sources(root)
    runtime_modules_bound(root, native_executor, fixture_fn, plan_type)
    source = read_pinned_source(root)
    case, fabric, plans = fixture_fn()
    baseline_hash = snapshot((case, fabric, plans))
    totals = {regime: {guard: {policy: {
        'cells': 0, 'full_native_equal': 0, 'functional_payload_equal': 0,
        'ACKs': 0, 'paid': 0, 'prepaid': 0, 'ACK_pregrants': 0,
        'consumer_first_ticks': 0, 'ACK_first_ticks': 0,
        'ready_ACK_candidates_withheld': 0, 'source_queue_collision_ticks': 0,
        'max_competing_consumer_streak': 0,
    } for policy in POLICIES} for guard, _, _ in GUARDS}
              for regime, _ in REGIMES}
    interventions = {x: {'cells': 0, 'native_restored': 0, 'ACKs': 0,
                         'paid': 0, 'source_queue_collisions': 0}
                     for x in INTERVENTIONS}
    compared_queue_cells = 0
    distinct_ACK_journal_cells = 0
    activated_bounded_turn_limit_cells = 0
    rows = []
    for i, (label, recipe) in enumerate(RECIPES):
        altered = build_workload(case, recipe)
        modes = []
        for j, (mode, enabled, priority) in enumerate(ARMS):
            capacities = {}
            for regime, capacity in REGIMES:
                signed_old = prev['paired_native_matrix'][i]['modes'][j][
                    'capacities'][regime]
                amended = (plans[0], replace(plans[1], fabric_slots_per_tick=capacity),
                           plans[2], plans[3])
                data = (altered, fabric, amended)
                digest = snapshot(data)
                captured_native = {}

                def capture(*args, **kwargs):
                    captured_native['result'] = native_executor(*args, **kwargs)
                    return captured_native['result']

                signed_native = _arm(capture, plan_type, altered, fabric, amended,
                    'v2v-v2x-native-'+regime, enabled, priority, digest, data)
                require(signed_native['whole_result_sha256'] ==
                        signed_old['signed_v2r_native_sha256'],
                        'v2v-v2x frozen native differs from signed v2stu original')
                native = captured_native['result']
                guards = {}
                for guard, forward, bv in GUARDS:
                    policies = {}
                    cache = {}
                    for policy in POLICIES:
                        _, summary, acks, paid, probes, captured, _ = _derived(
                            source, native_executor, plan_type, altered, fabric,
                            amended, enabled, priority, digest, data,
                            label=guard+'-'+policy, policy=policy,
                            forward=forward, bv=bv)
                        projected = captured['projected']
                        functional = _payload(projected['forward']) == _payload(
                            native['forward'])
                        strict = guard == 'strict_native_ready'
                        require(functional and (not strict or projected == native),
                                'v2v-v2x queue policy violated frozen source native-ready parity')
                        collision = sum(p['consumer_backlog_before'] > 0 and
                                        p['ready_ACKs_before'] > 0 for p in probes)
                        t = totals[regime][guard][policy]
                        t['cells'] += 1
                        t['full_native_equal'] += int(projected == native)
                        t['functional_payload_equal'] += int(functional)
                        t['ACKs'] += len(acks)
                        t['paid'] += len(paid)
                        t['prepaid'] += summary['concurrent_before_forward_applications']
                        t['ACK_pregrants'] += summary['pre_forward_actor_grants']
                        t['consumer_first_ticks'] += summary['consumer_first_ticks']
                        t['ACK_first_ticks'] += summary['ACK_first_ticks']
                        t['ready_ACK_candidates_withheld'] += summary[
                            'ready_ACK_candidates_withheld_pre_forward']
                        t['source_queue_collision_ticks'] += collision
                        t['max_competing_consumer_streak'] = max(
                            t['max_competing_consumer_streak'],
                            summary['max_observed_competing_consumer_streak'])
                        policies[policy] = {
                            'native_equal': projected == native,
                            'ACK_count': len(acks), 'paid_count': len(paid),
                            'pre_forward_paid': summary['concurrent_before_forward_applications'],
                            'source_queue_collision_ticks': collision,
                            'ACK_journal_sha256': sha256(canon(acks)).hexdigest(),
                            'consumer_journal_sha256': sha256(canon(paid)).hexdigest(),
                            'withheld_ready_ACKs': summary['ready_ACK_candidates_withheld_pre_forward'],
                            'max_competing_consumer_streak':
                                summary['max_observed_competing_consumer_streak'],
                            'forward_terminal_ticks': [x['timestamp'] for x in
                                projected['forward']['terminal']],
                        }
                        cache[policy] = (projected, acks, paid, probes)
                    first, consumer, bounded = (cache[k] for k in POLICIES)
                    if guard == 'actor_first_null_guard' and capacity == 1:
                        compared_queue_cells += int(
                            any(p['consumer_backlog_before'] and p['ready_ACKs_before']
                                for p in consumer[3]))
                        distinct_ACK_journal_cells += int(first[1] != consumer[1])
                        activated_bounded_turn_limit_cells += int(
                            any(p['consumer_priority_streak_before'] >= 1 and
                                p['consumer_backlog_before'] and p['ready_ACKs_before']
                                for p in bounded[3]))
                        for intervention in INTERVENTIONS:
                            _, s, a, consumed, probes, result, _ = _derived(
                                source, native_executor, plan_type, altered, fabric,
                                amended, enabled, priority, digest, data,
                                label='causal-'+intervention, policy='bounded-turns',
                                forward=False, bv=False, intervention=intervention)
                            native_restored = result['projected'] == native
                            if intervention in ('credit_zero', 'transport_loss'):
                                require(native_restored and not a and not consumed,
                                        'v2v-v2x causal null failed original native restoration')
                            counter = interventions[intervention]
                            counter['cells'] += 1
                            counter['native_restored'] += int(native_restored)
                            counter['ACKs'] += len(a)
                            counter['paid'] += len(consumed)
                            counter['source_queue_collisions'] += sum(
                                p['consumer_backlog_before'] and p['ready_ACKs_before']
                                for p in probes)
                    guards[guard] = policies
                capacities[regime] = {
                    'capacity': capacity,
                    'signed_native_sha256': signed_old['signed_v2r_native_sha256'],
                    'source_guard_policies': guards}
            modes.append({'mode': mode, 'capacities': capacities})
        rows.append({'label': label, 'recipe': [list(x) for x in recipe],
                     'modes': modes})
        require(snapshot((case, fabric, plans)) == baseline_hash,
                'v2v-v2x original fixture mutated by queue experiment')
    require(all(v['cells'] == 45 and v['functional_payload_equal'] == 45 for
                by_regime in totals.values() for by_guard in by_regime.values()
                for v in by_guard.values()) and
            all(v['full_native_equal'] == 45 for by_regime in totals.values()
                for v in by_regime['strict_native_ready'].values()) and
            compared_queue_cells > 0 and distinct_ACK_journal_cells > 0 and
            all(x['cells'] == 45 for x in interventions.values()) and
            interventions['credit_zero']['native_restored'] == 45 and
            interventions['transport_loss']['native_restored'] == 45 and
            activated_bounded_turn_limit_cells == 0 and
            source_pins(root) == before_pins and
            read_pinned_sources(root) == before_arch and
            read_pinned_source(root) == source and
            snapshot((case, fabric, plans)) == baseline_hash,
            'v2v-v2x cumulative queue precedence/causal source matrix incomplete')
    return {'paired_native_matrix': rows,
            'two_queue_policy_totals': totals,
            'causal_intervention_totals': interventions,
            'ready_queue_collision_cells': compared_queue_cells,
            'distinct_ACK_journal_policy_cells': distinct_ACK_journal_cells,
            'bounded_turn_limit_activated_cells': activated_bounded_turn_limit_cells,
            'native_original_runs': 90,
            'derived_policy_runs': 540,
            'derived_causal_intervention_runs': 135,
            'source_custody': True}


def build_report(prev, raw, result=None):
    validate_v2stu(prev, raw)
    require(result is None or
            (result['source_custody'] and result['native_original_runs'] == 90 and
             result['derived_policy_runs'] == 540 and
             result['derived_causal_intervention_runs'] == 135 and
             result['ready_queue_collision_cells'] > 0 and
             result['distinct_ACK_journal_policy_cells'] > 0),
            'v2v-v2x 15-by-3-by-2 signed research and ablation incomplete')
    return {
        'schema': SCHEMA,
        'status': STATUS if result else CONTRACT,
        'reference_v2stu_sha256': sha256(raw).hexdigest(),
        'cumulative_research_stages': [
            'v2v-source-delivered-ACK-vs-real-pre-forward-consumer-queue-precedence',
            'v2w-bounded-consumer-turn-preference-with-explicit-unproven-termination',
            'v2x-causal-loss-credit-zero-independent-resource-and-adversarial-audit',
        ],
        'new_native_runs': result['native_original_runs'] if result else 0,
        'new_derived_policy_runs': result['derived_policy_runs'] if result else 0,
        'new_derived_causal_intervention_runs': (
            result['derived_causal_intervention_runs'] if result else 0),
        'ready_queue_collision_cells': result['ready_queue_collision_cells'] if result else 0,
        'distinct_ACK_journal_policy_cells': (
            result['distinct_ACK_journal_policy_cells'] if result else 0),
        'bounded_turn_limit_activated_cells': (
            result['bounded_turn_limit_activated_cells'] if result else None),
        'two_queue_policy_totals': result['two_queue_policy_totals'] if result else None,
        'causal_intervention_totals': (
            result['causal_intervention_totals'] if result else None),
        'paired_native_matrix': result['paired_native_matrix'] if result else None,
        'derived_two_queue_priority_discrimination_proven': bool(result),
        'universal_ACK_fairness_or_starvation_freedom_proven': False,
        'frozen_native_actor_scheduler_or_learning_contract_proven': False,
        'native_operator_updates': 0,
        'next_gate': 'BLOCKED_NATIVE_QUEUE_ARBITRATION_AND_UNIVERSAL_LIVENESS_CONTRACT',
        'claims_excluded': list(EXCLUSIONS),
    }
