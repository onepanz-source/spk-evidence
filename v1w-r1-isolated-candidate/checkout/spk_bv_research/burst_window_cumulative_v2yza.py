"""v2y-v3a cumulative, causal ACK/consumer burst-window research matrix.

Uses *actual* pinned native emissions and a separate source-compiled derived
actor. No synthetic inbox records, native scheduler edits or liveness claims.
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
from spk_bv_research.actor_priority_contention_integration_v2m import _payload
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
    ActorQueuePlanV2v, DerivedActorQueueFairnessV2v,
    derive_queue_fairness_executor, POLICIES,
)
from spk_backvalidation_v2.derived_actor_burst_window_v2y import (
    BurstWindowPressurePlan, audit_burst_window, validate_burst_pressure,
)

SCHEMA = 'spk-bv-source-causal-multiturn-window-closure/v2y-v3a'
STATUS = 'DERIVED_ACTIVATED_ACK_WINDOW_SOURCE_BURST_CONDITIONAL_NO_NATIVE_LIVENESS'
CONTRACT = 'V2Y_V3A_SIGNED_V2VWX_PREDECESSOR_ONLY'
PREDECESSOR_SHA = 'c7cb06097b6d09f30a11a810cfd5b7e3197a773a2a0a7e29766f55bd41a553ef'
INTERVENTIONS = ('ACK_quota_one', 'latency_one', 'consumer_zero',
                 'credit_zero', 'transport_loss')
GUARDS = (('strict_native_ready', True, True),
          ('actor_first_null_guard', False, False))
EXCLUSIONS = (
    'conditional_finite_window_is_not_universal_starvation_freedom',
    'ACK_queue_preference_is_not_an_unconditional_service_or_progress_grant',
    'native_forward_or_feedback_guard_can_preempt_any_derived_queue',
    'two_PE_capacity_is_an_explicit_original_native_model_intervention',
    'two_global_ACK_services_and_latency_two_are_derived_research_controls',
    'only_source_ingress_and_receiver_owned_judgments_can_enter_queue',
    'loss_overflow_and_unserviced_ACK_are_not_negative_certificates',
    'no_frozen_native_actor_intake_priority_learning_or_cross_node_authority',
    'no_universal_horizon_quorum_network_or_hardware_calibration',
)


def validate_v2vwx(prev, raw):
    require(type(prev) is dict and type(raw) is bytes and canon(prev) == raw and
            sha256(raw).hexdigest() == PREDECESSOR_SHA,
            'v2y-v3a noncanonical or altered signed v2vwx predecessor')
    require(prev.get('schema') ==
            'spk-bv-pinned-two-queue-precedence-and-bounded-window-discriminator/v2v-v2x'
            and prev.get('status') ==
            'DERIVED_TWO_QUEUE_PRIORITY_CAUSAL_DISCRIMINATION_NO_NATIVE_LIVENESS_CONTRACT'
            and prev.get('reference_v2stu_sha256') ==
            '418f8154b25ed78bcbb5dc6ba5f8a0968dc107425d43c2e38c71ba2485b11975'
            and prev.get('new_native_runs') == 90 and
            prev.get('new_derived_policy_runs') == 540 and
            prev.get('new_derived_causal_intervention_runs') == 135 and
            prev.get('ready_queue_collision_cells') == 37 and
            prev.get('distinct_ACK_journal_policy_cells') == 37 and
            prev.get('bounded_turn_limit_activated_cells') == 0 and
            prev.get('derived_two_queue_priority_discrimination_proven') is True and
            prev.get('universal_ACK_fairness_or_starvation_freedom_proven') is False and
            prev.get('frozen_native_actor_scheduler_or_learning_contract_proven') is False
            and prev.get('native_operator_updates') == 0 and
            prev.get('next_gate') ==
                'BLOCKED_NATIVE_QUEUE_ARBITRATION_AND_UNIVERSAL_LIVENESS_CONTRACT',
            'v2y-v3a predecessor exclusion or prior outcome drift')
    rows = prev.get('paired_native_matrix')
    require(type(rows) is list and len(rows) == len(RECIPES),
            'v2y-v3a pinned 15 source workloads missing')
    for (label, recipe), row in zip(RECIPES, rows):
        require(row.get('label') == label and
                row.get('recipe') == [list(x) for x in recipe] and
                [x.get('mode') for x in row.get('modes', [])] ==
                    [x for x, _, _ in ARMS],
                'v2y-v3a source workload or native BV mode mismatch')
        for mode in row['modes']:
            for regime, budget in (('original_capacity', 3),
                                   ('contended_capacity', 1)):
                cell = mode.get('capacities', {}).get(regime, {})
                require(cell.get('capacity') == budget and
                        len(cell.get('signed_native_sha256', '')) == 64 and
                        all(cell.get('source_guard_policies', {}).get(
                            'strict_native_ready', {}).get(name, {}).get(
                                'native_equal') is True for name in POLICIES),
                        'v2y-v3a signed native source matrix incomplete')
    return True


def _run_derived(source, native_executor, plan_type, altered, fabric, plans,
                 enabled, priority, digest, data, *, label, policy,
                 forward, bv, intervention='normal'):
    require(policy in POLICIES and intervention in ('normal', *INTERVENTIONS),
            'v2y invalid derivative intervention')
    port = ReceiverPortV2h(
        latency=1 if intervention == 'latency_one' else 2,
        accept=(lambda _: False) if intervention == 'transport_loss' else None)
    service = ShadowServicePlanV2j(
        max_per_tick=1 if intervention == 'ACK_quota_one' else 2)
    consumer = ConcurrentConsumerPlan(
        max_per_tick=0 if intervention == 'consumer_zero' else 1)
    credit = (ActorCreditPlanV2l(max_abs_credit=0)
              if intervention == 'credit_zero' else ActorCreditPlanV2l())
    actor = DerivedActorQueueFairnessV2v(
        port, queue_plan=ActorQueuePlanV2v(policy),
        admission_plan=CausalAdmissionPlanV2o(forward, bv),
        service_plan=service, concurrent_plan=consumer, credit_plan=credit)
    observer = CallsiteObserver()
    executor, _, semantic, resources = derive_queue_fairness_executor(
        source, native_executor, port, actor, observer)
    captured = {}

    def run(*args, **kwargs):
        captured['derived'] = executor(*args, **kwargs)
        captured['native_projection'] = actor.project_original_native_result(
            captured['derived'])
        return captured['native_projection']

    _arm(run, plan_type, altered, fabric, plans, label, enabled,
         priority, digest, data)
    summary = actor.summary()
    ACKs, paid = actor.credit_journal(), actor.concurrent_journal()
    probes = actor.queue_fairness_probes()
    require(semantic == (('batch', 194), ('clock', 125),
                         ('emission', 217), ('ingress', 136)) and
            resources == (158, 296, 307) and not observer.overflow and
            not observer.sink_failed and observer.counts()['_admit'] == 1 and
            observer.counts()['_admit_plan'] == 1 and
            summary['queue_priority_policy'] == policy and
            summary['native_operator_updates'] == 0 and
            summary['frozen_actor_state_changed'] is False and
            summary['absence_certificates'] == 0 and
            summary['derived_actor_credit_ack_count'] == len(ACKs) and
            summary['concurrent_paid_applications'] == len(paid) and
            summary['concurrent_consumer_PE_units'] == len(paid) and
            summary['concurrent_consumer_memory_units'] == 2*len(paid) and
            summary['concurrent_pending_acks'] == len(ACKs)-len(paid) and
            len(probes) == summary['native_original_timeline_rows'],
            'v2y-v3a source ownership, ACK/consumer charges or native probe drift')
    if intervention in ('normal', 'ACK_quota_one', 'latency_one'):
        require(len(ACKs) == len(paid),
                'v2y-v3a normal causal service did not finish paid consumption')
    if intervention == 'consumer_zero':
        require(not paid and summary['concurrent_pending_acks'] == len(ACKs),
                'v3a zero consumer minted a paid receipt')
    if intervention in ('credit_zero', 'transport_loss'):
        require(not ACKs and not paid,
                'v3a lost or policy-blocked source minted ACK/consumer credit')
    witness = audit_burst_window(actor) if intervention == 'normal' else None
    return summary, ACKs, paid, probes, witness, captured['native_projection']


def experiment(prev, raw, *, root: Path, fixture_fn, native_executor, plan_type):
    validate_v2vwx(prev, raw)
    validate_burst_pressure(BurstWindowPressurePlan())
    root = root.resolve(strict=True)
    source = read_pinned_source(root)
    before_pins = source_pins(root)
    architecture = read_pinned_sources(root)
    runtime_modules_bound(root, native_executor, fixture_fn, plan_type)
    case, fabric, plans = fixture_fn()
    baseline = snapshot((case, fabric, plans))
    totals = {guard: {p: {'cells': 0, 'full_native_parity': 0,
                          'functional_payload_parity': 0, 'ACKs': 0,
                          'paid_consumer_receipts': 0, 'collision_ticks': 0,
                          'eligible_bounded_window_ticks': 0,
                          'forced_bounded_ACK_preference': 0,
                          'forced_window_real_ACK_grants': 0,
                          'max_competing_consumer_streak': 0}
                     for p in POLICIES} for guard, _, _ in GUARDS}
    interventions = {name: {'cells': 0, 'native_restored': 0, 'ACKs': 0,
                            'paid': 0, 'competing_streak_two_cells': 0}
                     for name in INTERVENTIONS}
    source_window_cells = 0
    active_bounded_window_cells = 0
    active_bounded_window_ticks = 0
    observed_unbounded_streak_two_cells = 0
    bounded_max_streak_above_one_cells = 0
    changed_ACK_journal_by_bound_cells = 0
    changed_consumer_journal_by_bound_cells = 0
    null_policy_terminal_payload_parity_cells = 0
    native_rows = []
    for label, recipe in RECIPES:
        altered = build_workload(case, recipe)
        modes = []
        for mode, enabled, priority in ARMS:
            adjusted = (plans[0], replace(plans[1], fabric_slots_per_tick=2),
                        plans[2], plans[3])
            data = (altered, fabric, adjusted)
            digest = snapshot(data)
            captured = {}

            def capture(*args, **kwargs):
                captured['native'] = native_executor(*args, **kwargs)
                return captured['native']

            native_signed = _arm(capture, plan_type, altered, fabric, adjusted,
                                 'v2y-source-native-two-PE', enabled,
                                 priority, digest, data)
            native = captured['native']
            guards = {}
            for guard, forward, bv in GUARDS:
                policies = {}
                outcomes = {}
                for policy in POLICIES:
                    summary, ACKs, paid, probes, witness, projected = _run_derived(
                        source, native_executor, plan_type, altered, fabric,
                        adjusted, enabled, priority, digest, data,
                        label='v2y-'+guard+'-'+policy, policy=policy,
                        forward=forward, bv=bv)
                    strict = guard == 'strict_native_ready'
                    functional = _payload(projected['forward']) == _payload(
                        native['forward'])
                    require(functional and (not strict or projected == native),
                            'v2y-v3a conditional queue policy changed frozen native contract')
                    t = totals[guard][policy]
                    t['cells'] += 1
                    t['full_native_parity'] += int(projected == native)
                    t['functional_payload_parity'] += int(functional)
                    t['ACKs'] += len(ACKs)
                    t['paid_consumer_receipts'] += len(paid)
                    t['collision_ticks'] += witness['source_queue_collision_ticks']
                    t['eligible_bounded_window_ticks'] += witness[
                        'eligible_bounded_turn_windows']
                    t['forced_bounded_ACK_preference'] += witness[
                        'forced_ACK_preference_windows']
                    t['forced_window_real_ACK_grants'] += witness[
                        'ACK_pre_forward_grants_on_forced_windows']
                    t['max_competing_consumer_streak'] = max(
                        t['max_competing_consumer_streak'],
                        witness['max_competing_consumer_streak'])
                    policies[policy] = {
                        'native_equal': projected == native,
                        'functional_payload_equal': functional,
                        'ACK_count': len(ACKs), 'paid_count': len(paid),
                        'ACK_journal_sha256': sha256(canon(ACKs)).hexdigest(),
                        'consumer_journal_sha256': sha256(canon(paid)).hexdigest(),
                        'source_queue_collision_ticks': witness[
                            'source_queue_collision_ticks'],
                        'eligible_bounded_window_ticks': witness[
                            'eligible_bounded_turn_windows'],
                        'actual_bounded_window_ACK_grants': witness[
                            'ACK_pre_forward_grants_on_forced_windows'],
                        'max_competing_consumer_streak': witness[
                            'max_competing_consumer_streak'],
                    }
                    outcomes[policy] = (ACKs, paid, probes, witness, projected)
                if guard == 'actor_first_null_guard':
                    a, unbounded, bounded = (outcomes[p] for p in POLICIES)
                    forcing = bounded[3]['forced_ACK_preference_windows']
                    source_window_cells += int(bounded[3]['source_queue_collision_ticks'] > 0)
                    active_bounded_window_cells += int(forcing > 0)
                    active_bounded_window_ticks += forcing
                    observed_unbounded_streak_two_cells += int(
                        unbounded[3]['max_competing_consumer_streak'] >= 2)
                    bounded_max_streak_above_one_cells += int(
                        bounded[3]['max_competing_consumer_streak'] > 1)
                    changed_ACK_journal_by_bound_cells += int(
                        unbounded[0] != bounded[0])
                    changed_consumer_journal_by_bound_cells += int(
                        unbounded[1] != bounded[1])
                    null_policy_terminal_payload_parity_cells += int(
                        _payload(a[4]['forward']) == _payload(unbounded[4]['forward'])
                        == _payload(bounded[4]['forward']))
                    for intervention in INTERVENTIONS:
                        s, ACKs, paid, probes, _, projected = _run_derived(
                            source, native_executor, plan_type, altered, fabric,
                            adjusted, enabled, priority, digest, data,
                            label='v3a-'+intervention,
                            policy='bounded-turns', forward=False, bv=False,
                            intervention=intervention)
                        counter = interventions[intervention]
                        counter['cells'] += 1
                        counter['native_restored'] += int(projected == native)
                        counter['ACKs'] += len(ACKs)
                        counter['paid'] += len(paid)
                        counter['competing_streak_two_cells'] += int(
                            s['max_observed_competing_consumer_streak'] >= 2)
                        if intervention in ('credit_zero', 'transport_loss'):
                            require(projected == native and not ACKs and not paid,
                                    'v3a causal null did not restore original native')
                guards[guard] = policies
            modes.append({'mode': mode, 'source_native_sha256':
                          native_signed['whole_result_sha256'],
                          'guards': guards})
        native_rows.append({'label': label, 'recipe': [list(x) for x in recipe],
                            'modes': modes})
        require(snapshot((case, fabric, plans)) == baseline,
                'v2y-v3a source native workload unexpectedly mutated')
    require(all(t['cells'] == 45 and t['functional_payload_parity'] == 45
                for guards in totals.values() for t in guards.values()) and
            all(t['full_native_parity'] == 45 for t in
                totals['strict_native_ready'].values()) and
            all(v['cells'] == 45 for v in interventions.values()) and
            interventions['credit_zero']['native_restored'] == 45 and
            interventions['transport_loss']['native_restored'] == 45 and
            observed_unbounded_streak_two_cells > 0 and
            active_bounded_window_cells > 0 and
            active_bounded_window_ticks > 0 and
            bounded_max_streak_above_one_cells == 0 and
            changed_ACK_journal_by_bound_cells > 0 and
            changed_consumer_journal_by_bound_cells > 0 and
            null_policy_terminal_payload_parity_cells == 45 and
            interventions['ACK_quota_one']['competing_streak_two_cells'] == 0 and
            interventions['latency_one']['competing_streak_two_cells'] == 0 and
            interventions['consumer_zero']['paid'] == 0 and
            source_pins(root) == before_pins and
            read_pinned_sources(root) == architecture and
            read_pinned_source(root) == source and
            snapshot((case, fabric, plans)) == baseline,
            'v2y-v3a source-backed burst window or adversarial causal matrix incomplete')
    return {
        'native_matrix': native_rows,
        'conditional_window_totals': totals,
        'causal_pressure_ablations': interventions,
        'new_native_runs': 45,
        'new_derived_policy_runs': 270,
        'new_derived_ablation_runs': 225,
        'source_window_cells': source_window_cells,
        'bounded_window_activated_cells': active_bounded_window_cells,
        'bounded_window_activated_ticks': active_bounded_window_ticks,
        'unbounded_two_turn_streak_cells': observed_unbounded_streak_two_cells,
        'bounded_overrun_cells': bounded_max_streak_above_one_cells,
        'ACK_journal_bound_intervention_cells': changed_ACK_journal_by_bound_cells,
        'consumer_journal_bound_intervention_cells':
            changed_consumer_journal_by_bound_cells,
        'null_policy_payload_parity_cells': null_policy_terminal_payload_parity_cells,
        'source_frozen': True,
    }


def build_report(prev, raw, result=None):
    validate_v2vwx(prev, raw)
    require(result is None or (result['source_frozen'] and
        result['new_native_runs'] == 45 and
        result['new_derived_policy_runs'] == 270 and
        result['new_derived_ablation_runs'] == 225 and
        result['bounded_window_activated_cells'] > 0 and
        result['ACK_journal_bound_intervention_cells'] > 0 and
        result['bounded_overrun_cells'] == 0),
        'v2y-v3a cumulative finite window matrix incomplete')
    return {
        'schema': SCHEMA,
        'status': STATUS if result else CONTRACT,
        'reference_v2vwx_sha256': sha256(raw).hexdigest(),
        'cumulative_research_stages': [
            'v2y-source-backed-intermediate-two-PE-double-ACK-burst-pressure',
            'v2z-measured-multi-turn-bounded-ACK-preference-and-real-grant-witness',
            'v3a-five-causal-null-and-adversarial-native-projection-closure',
        ],
        'new_native_runs': result['new_native_runs'] if result else 0,
        'new_derived_policy_runs': result['new_derived_policy_runs'] if result else 0,
        'new_derived_ablation_runs': result['new_derived_ablation_runs'] if result else 0,
        'source_queue_collision_cells': result['source_window_cells'] if result else 0,
        'bounded_window_activated_cells': result[
            'bounded_window_activated_cells'] if result else 0,
        'bounded_window_activated_ticks': result[
            'bounded_window_activated_ticks'] if result else 0,
        'unbounded_two_turn_streak_cells': result[
            'unbounded_two_turn_streak_cells'] if result else 0,
        'bounded_overrun_cells': result['bounded_overrun_cells'] if result else None,
        'ACK_journal_bound_intervention_cells': result[
            'ACK_journal_bound_intervention_cells'] if result else 0,
        'consumer_journal_bound_intervention_cells': result[
            'consumer_journal_bound_intervention_cells'] if result else 0,
        'null_policy_payload_parity_cells': result[
            'null_policy_payload_parity_cells'] if result else 0,
        'conditional_window_totals': result[
            'conditional_window_totals'] if result else None,
        'causal_pressure_ablations': result[
            'causal_pressure_ablations'] if result else None,
        'native_matrix': result['native_matrix'] if result else None,
        'derived_finite_bounded_window_source_witness': bool(result),
        'universal_ACK_or_consumer_liveness_proven': False,
        'native_queue_arbitration_or_learning_proven': False,
        'native_operator_updates': 0,
        'next_gate': 'BLOCKED_UNIVERSAL_PROGRESS_NATIVE_ACTOR_POLICY_AND_LEARNING',
        'claims_excluded': list(EXCLUSIONS),
    }
