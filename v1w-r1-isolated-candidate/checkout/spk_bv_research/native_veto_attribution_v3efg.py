"""v3e-v3g cumulative source-backed native-guard factorial and tail boundary.

All actor policies are derived, with exact frozen-native source pins. A guard
counterfactual is not identified as a safe native scheduler policy change.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import (
    require, runtime_modules_bound, source_pins, snapshot,
)
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources
from spk_bv_research.actor_priority_contention_integration_v2m import _payload
from spk_bv_research.link_pressure_v0u import ARMS, _arm
from spk_bv_research.burst_window_cumulative_v2yza import _run_derived
from spk_bv_research.episode_wait_prefix_integration_v3bcd import SCHEDULES
from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver, read_pinned_source,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import ReceiverPortV2h
from spk_backvalidation_v2.derived_actor_control_service_v2j import ShadowServicePlanV2j
from spk_backvalidation_v2.derived_causal_admission_v2o import CausalAdmissionPlanV2o
from spk_backvalidation_v2.derived_actor_queue_fairness_v2v import (
    ActorQueuePlanV2v, DerivedActorQueueFairnessV2v,
    derive_queue_fairness_executor, POLICIES,
)
from spk_backvalidation_v2.derived_native_veto_wait_audit_v3e import (
    CLASSES, audit_native_wait_overlap,
)

SCHEMA = 'spk-bv-native-ready-guard-factorial-wait-tail-closure/v3e-v3g'
STATUS = 'DERIVED_NATIVE_GUARD_FACTORIAL_WAIT_OVERLAP_NO_UNIVERSAL_ACK_DEADLINE'
CONTRACT = 'V3E_V3G_SIGNED_V3BCD_PREDECESSOR_ONLY'
PREDECESSOR_SHA = 'd347de60d14893380c5433993d2c6aefee46118bf6dbff6da13198d272ac4b90'
ADDITIONAL_SCHEDULES = (
    ('eight_four_gap', (1, 5, 9, 13, 17, 21, 25, 29)),
    ('eight_late', (4, 8, 12, 16, 20, 24, 28, 32)),
    ('eight_paired_bursts', (1, 2, 7, 8, 15, 16, 23, 24)),
)
ALL_SCHEDULES = SCHEDULES + ADDITIONAL_SCHEDULES
GUARD_FACTORIAL = (
    ('both_native_guards', True, True),
    ('forward_only_guard', True, False),
    ('feedback_only_guard', False, True),
    ('no_native_guard', False, False),
)
EXCLUSIONS = (
    'observed_wait_overlap_is_not_individual_tick_causal_attribution',
    'relaxing_a_native_guard_is_a_derived_counterfactual_not_native_adoption',
    'full_native_projection_only_required_under_both_native_guards',
    'functional_payload_parity_does_not_imply_timing_or_resource_parity',
    'tail_off_undelivered_or_unserviced_ACK_is_not_negative_receiver_judgment',
    'finite_source_last_veto_and_tail_clearance_do_not_prove_global_deadline',
    'no_native_actor_learning_starvation_freedom_or_hardware_claim',
)


def validate_v3bcd(prev, raw):
    require(type(prev) is dict and type(raw) is bytes and canon(prev) == raw and
            sha256(raw).hexdigest() == PREDECESSOR_SHA,
            'v3e-v3g signed/canonical v3bcd predecessor drift')
    require(prev.get('schema') ==
            'spk-bv-source-episode-prefix-and-native-veto-wait-discriminator/v3b-v3d'
            and prev.get('status') ==
            'DERIVED_SOURCE_EPISODE_PREFIX_ACK_WAIT_NATIVE_VETO_COUNTEREXAMPLE'
            and prev.get('reference_v2yza_sha256') ==
            '56d9208e1f0fd2f8dbad6c77030582f7dff8d7fdd1052ce7c2bc8a8c1fcb80f8'
            and prev.get('new_original_native_runs') == 18
            and prev.get('new_derived_queue_runs') == 108
            and prev.get('new_derived_null_runs') == 36
            and prev.get('null_guard_bounded_max_ACK_wait_ticks') == 1
            and prev.get('null_guard_unbounded_max_ACK_wait_ticks') == 3
            and prev.get('strict_native_veto_max_ACK_wait_ticks') == 29
            and prev.get('prefix_causal_nonanticipation', {}).get('comparisons') == 72
            and prev.get('native_veto_global_deadline_counterexample_observed') is True
            and prev.get('universal_ACK_or_consumer_liveness_proven') is False
            and prev.get('native_operator_updates') == 0
            and prev.get('next_gate') ==
            'BLOCKED_NATIVE_GLOBAL_PROGRESS_BEYOND_SOURCE_WINDOW_AND_LEARNING',
            'v3e-v3g predecessor safety/negative claims drift')
    require(len(prev.get('source_episode_matrix', ())) == 6 and
            [r.get('source_schedule') for r in prev['source_episode_matrix']] ==
            [label for label, _ in SCHEDULES] and
            all([mode.get('mode') for mode in row['modes']] ==
                [mode for mode, _, _ in ARMS]
                for row in prev['source_episode_matrix']),
            'v3e-v3g signed native source episodes incomplete')
    return True


def _run_no_tail(source, native_executor, plan_type, case, fabric, plans,
                 enabled, priority, digest, data):
    """Real derived source run with ACK tail explicitly disabled, not simulated."""
    port = ReceiverPortV2h(latency=2)
    actor = DerivedActorQueueFairnessV2v(
        port, queue_plan=ActorQueuePlanV2v('bounded-turns'),
        admission_plan=CausalAdmissionPlanV2o(True, True),
        service_plan=ShadowServicePlanV2j(max_per_tick=2, max_tail_ticks=0))
    observer = CallsiteObserver()
    executor, _, semantic, anchors = derive_queue_fairness_executor(
        source, native_executor, port, actor, observer)
    capture = {}

    def run(*args, **kwargs):
        capture['derived'] = executor(*args, **kwargs)
        capture['projected'] = actor.project_original_native_result(
            capture['derived'])
        return capture['projected']

    _arm(run, plan_type, case, fabric, plans, 'v3g-tail-off', enabled,
         priority, digest, data)
    summary = actor.summary()
    ACKs, paid = actor.credit_journal(), actor.concurrent_journal()
    require(semantic == (('batch', 194), ('clock', 125), ('emission', 217),
                         ('ingress', 136)) and anchors == (158, 296, 307) and
            not observer.overflow and not observer.sink_failed and
            summary['native_operator_updates'] == 0 and
            summary['absence_certificates'] == 0 and
            summary['frozen_actor_state_changed'] is False and
            summary['derived_control_tail_grants'] == 0 and
            summary['derived_actor_credit_ack_count'] == len(ACKs) and
            summary['concurrent_paid_applications'] == len(paid),
            'v3g tail-off source ownership/actual credit audit drift')
    return summary, ACKs, paid, capture['projected'], port.summary()


def experiment(prev, raw, *, root: Path, fixture_fn, native_executor, plan_type):
    validate_v3bcd(prev, raw)
    root = root.resolve(strict=True)
    source = read_pinned_source(root)
    pins = source_pins(root)
    arch = read_pinned_sources(root)
    runtime_modules_bound(root, native_executor, fixture_fn, plan_type)
    sums = {label: {policy: {
        'cells': 0, 'native_exact': 0, 'functional_equal': 0,
        'source_ACKs': 0, 'paid_consumer_receipts': 0,
        'ACK_wait_max_ticks': 0, 'ACK_wait_total_ticks': 0,
        'native_veto_ticks': 0, 'source_unblocked_ACK_opportunities': 0,
        'source_authorized_pregrants': 0,
        'wait_overlap': dict.fromkeys(CLASSES, 0),
    } for policy in POLICIES} for label, _, _ in GUARD_FACTORIAL}
    nulls = {name: {'cells': 0, 'native_restored': 0, 'ACKs': 0, 'paid': 0}
             for name in ('credit_zero', 'transport_loss')}
    no_tail = {'cells': 0, 'native_exact': 0, 'source_ACKs': 0,
               'paid': 0, 'delivered_unacked': 0, 'no_negative_from_pending': 0,
               'partial_service_cells': 0}
    rows = []
    contrasts = {'cells': 0, 'guard_relaxations_functional_equal': 0,
                 'forward_guard_off_reduces_max_wait': 0,
                 'feedback_guard_off_reduces_max_wait': 0,
                 'both_off_reduces_max_wait': 0,
                 'full_native_parity_lost_under_some_relaxation': 0}
    for label, ticks in ALL_SCHEDULES:
        case, fabric, plans = fixture_fn(ticks=ticks)
        require(tuple(e.timestamp for e in case.events) == ticks and
                len(ticks) <= 8 and all(e.node_id == 'A' and e.channel == 0
                                        for e in case.events),
                'v3e unauthorised native input schedule')
        altered = (plans[0], replace(plans[1], fabric_slots_per_tick=2),
                   plans[2], plans[3])
        data = (case, fabric, altered)
        digest = snapshot(data)
        modes = []
        for mode, enabled, priority in ARMS:
            saved = {}

            def capture(*args, **kwargs):
                saved['native'] = native_executor(*args, **kwargs)
                return saved['native']

            original = _arm(capture, plan_type, case, fabric, altered,
                            'v3e-native-'+label+'-'+mode, enabled, priority,
                            digest, data)
            native = saved['native']
            guards = {}
            in_cell = {}
            for guard_label, forward, feedback in GUARD_FACTORIAL:
                policies = {}
                for policy in POLICIES:
                    summary, ACKs, paid, probes, witness, projected = _run_derived(
                        source, native_executor, plan_type, case, fabric,
                        altered, enabled, priority, digest, data,
                        label='v3e-'+label+'-'+guard_label+'-'+policy,
                        policy=policy, forward=forward, bv=feedback)
                    audit = audit_native_wait_overlap(
                        ACKs, paid, probes, witness, policy=policy,
                        protect_forward=forward, protect_feedback=feedback)
                    exact = projected == native
                    functional = _payload(projected['forward']) == _payload(
                        native['forward'])
                    require(functional and (guard_label != 'both_native_guards' or
                                            exact),
                            'v3e full strict native projection or functional result drift')
                    total = sums[guard_label][policy]
                    total['cells'] += 1
                    total['native_exact'] += int(exact)
                    total['functional_equal'] += int(functional)
                    total['source_ACKs'] += len(ACKs)
                    total['paid_consumer_receipts'] += len(paid)
                    total['ACK_wait_max_ticks'] = max(total['ACK_wait_max_ticks'],
                                                       audit['ACK_wait_max_ticks'])
                    total['ACK_wait_total_ticks'] += audit['ACK_wait_total_ticks']
                    total['native_veto_ticks'] += sum(
                        audit['native_probe_tick_partition'][c] for c in CLASSES[:3])
                    total['source_unblocked_ACK_opportunities'] += audit[
                        'ready_ACK_unblocked_native_ticks']
                    total['source_authorized_pregrants'] += audit[
                        'actually_resource_charged_pre_forward_ACK_grants']
                    for c in CLASSES:
                        total['wait_overlap'][c] += audit[
                            'ACK_wait_tick_overlap_partition'][c]
                    in_cell[(guard_label, policy)] = (audit, exact)
                    policies[policy] = {
                        'full_native_equal': exact,
                        'functional_payload_equal': functional,
                        'ACK_count': len(ACKs), 'paid_count': len(paid),
                        'wait_max_ticks': audit['ACK_wait_max_ticks'],
                        'wait_total_ticks': audit['ACK_wait_total_ticks'],
                        'wait_overlap': audit['ACK_wait_tick_overlap_partition'],
                        'source_native_last_tick': audit['source_native_last_tick'],
                        'ACK_journal_sha256': sha256(canon(ACKs)).hexdigest(),
                        'paid_journal_sha256': sha256(canon(paid)).hexdigest(),
                    }
                guards[guard_label] = policies
            for policy in POLICIES:
                strict = in_cell[('both_native_guards', policy)][0][
                    'ACK_wait_max_ticks']
                forward_only = in_cell[('forward_only_guard', policy)][0][
                    'ACK_wait_max_ticks']
                feedback_only = in_cell[('feedback_only_guard', policy)][0][
                    'ACK_wait_max_ticks']
                none = in_cell[('no_native_guard', policy)][0]['ACK_wait_max_ticks']
                contrasts['cells'] += 1
                contrasts['guard_relaxations_functional_equal'] += 1
                contrasts['forward_guard_off_reduces_max_wait'] += int(
                    feedback_only < strict)
                contrasts['feedback_guard_off_reduces_max_wait'] += int(
                    forward_only < strict)
                contrasts['both_off_reduces_max_wait'] += int(none < strict)
                contrasts['full_native_parity_lost_under_some_relaxation'] += int(
                    any(not in_cell[(g, policy)][1] for g in (
                        'forward_only_guard', 'feedback_only_guard',
                        'no_native_guard')))
            # Explicit ablations under both-guards-off are independent of
            # strict native guardedness: absent controls restore native output.
            for intervention in nulls:
                _, ACKs, paid, _, _, projected = _run_derived(
                    source, native_executor, plan_type, case, fabric, altered,
                    enabled, priority, digest, data,
                    label='v3g-null-'+label+'-'+intervention,
                    policy='bounded-turns', forward=False, bv=False,
                    intervention=intervention)
                require(projected == native and not ACKs and not paid,
                        'v3g null causal control altered frozen native result')
                n = nulls[intervention]
                n['cells'] += 1
                n['native_restored'] += 1
            tail_summary, tail_acks, tail_paid, tail_projected, receiver = (
                _run_no_tail(source, native_executor, plan_type, case, fabric,
                             altered, enabled, priority, digest, data))
            require(tail_projected == native and
                    len(tail_paid) <= len(tail_acks) and
                    tail_summary['derived_control_tail_grants'] == 0 and
                    receiver['absence_certificates'] == 0,
                    'v3g no-tail fabricated an ACK, negative proof or native mutation')
            no_tail['cells'] += 1
            no_tail['native_exact'] += 1
            no_tail['source_ACKs'] += len(tail_acks)
            no_tail['paid'] += len(tail_paid)
            no_tail['delivered_unacked'] += tail_summary[
                'delivered_other_unconsumed_pending']
            no_tail['no_negative_from_pending'] += int(
                receiver['absence_certificates'] == 0)
            no_tail['partial_service_cells'] += int(
                tail_summary['delivered_other_unconsumed_pending'] > 0)
            modes.append({'mode': mode,
                          'source_native_sha256': original['whole_result_sha256'],
                          'guards': guards,
                          'tail_off': {'acked': len(tail_acks),
                                       'paid': len(tail_paid),
                                       'unconsumed_delivered': tail_summary[
                                           'delivered_other_unconsumed_pending']}})
        rows.append({'schedule': label, 'external_native_ticks': list(ticks),
                     'modes': modes})
        require(snapshot((case, fabric, altered)) == digest,
                'v3e mutated native fixture or resource plan')
    native_cells = len(ALL_SCHEDULES)*len(ARMS)
    require(all(t['cells'] == native_cells and
                t['functional_equal'] == native_cells and
                sum(t['wait_overlap'].values()) == t['ACK_wait_total_ticks']
                for guard in sums.values() for t in guard.values()) and
            all(sums['both_native_guards'][p]['native_exact'] == native_cells
                for p in POLICIES) and
            contrasts['cells'] == native_cells*len(POLICIES) and
            contrasts['feedback_guard_off_reduces_max_wait'] > 0 and
            contrasts['full_native_parity_lost_under_some_relaxation'] > 0 and
            all(x['cells'] == x['native_restored'] == native_cells
                for x in nulls.values()) and
            no_tail['cells'] == no_tail['native_exact'] == native_cells and
            no_tail['partial_service_cells'] > 0 and
            source_pins(root) == pins and read_pinned_source(root) == source and
            read_pinned_sources(root) == arch,
            'v3e-v3g factorial/native/counterexample/tail closure failed')
    return {
        'source_matrix': rows,
        'guard_factorial_totals': sums,
        'factorial_contrasts': contrasts,
        'causal_null_totals': nulls,
        'tail_disabled_observations': no_tail,
        'new_native_runs': native_cells,
        'new_derived_policy_runs': native_cells*len(GUARD_FACTORIAL)*len(POLICIES),
        'new_null_runs': native_cells*len(nulls),
        'new_tail_off_runs': native_cells,
        'new_extended_schedule_contexts': len(ADDITIONAL_SCHEDULES)*len(ARMS),
        'source_pins_preserved': True,
    }


def build_report(prev, raw, result=None):
    validate_v3bcd(prev, raw)
    require(result is None or (
        result['source_pins_preserved'] and
        result['new_native_runs'] == 27 and
        result['new_derived_policy_runs'] == 324 and
        result['new_null_runs'] == 54 and
        result['new_tail_off_runs'] == 27 and
        result['factorial_contrasts']['cells'] == 81 and
        result['tail_disabled_observations']['partial_service_cells'] > 0),
        'v3e-v3g missing source native factorial/tail evidence')
    return {
        'schema': SCHEMA,
        'status': STATUS if result else CONTRACT,
        'reference_v3bcd_sha256': sha256(raw).hexdigest(),
        'cumulative_research_stages': [
            'v3e-2x2-forward-feedback-native-guard-factorial',
            'v3f-exhaustive-source-native-veto-ACK-wait-tick-partition',
            'v3g-real-derived-no-tail-and-null-service-boundary',
        ],
        'new_native_runs': result['new_native_runs'] if result else 0,
        'new_derived_policy_runs': result['new_derived_policy_runs'] if result else 0,
        'new_null_runs': result['new_null_runs'] if result else 0,
        'new_tail_off_runs': result['new_tail_off_runs'] if result else 0,
        'new_extended_schedule_contexts':
            result['new_extended_schedule_contexts'] if result else 0,
        'guard_factorial_totals': result['guard_factorial_totals'] if result else None,
        'factorial_contrasts': result['factorial_contrasts'] if result else None,
        'causal_null_totals': result['causal_null_totals'] if result else None,
        'tail_disabled_observations':
            result['tail_disabled_observations'] if result else None,
        'source_matrix': result['source_matrix'] if result else None,
        'finite_source_guard_wait_overlap_measured': bool(result),
        'strict_full_native_projection_preserved': bool(result),
        'guard_relaxation_functional_native_equivalence_only': bool(result),
        'universal_ACK_deadline_or_native_learning_proven': False,
        'frozen_native_scheduler_actor_contract_modified': False,
        'native_operator_updates': 0,
        'next_gate': 'BLOCKED_GLOBAL_ACK_PROGRESS_WITHOUT_NATIVE_SERVICE_GUARANTEE',
        'claims_excluded': list(EXCLUSIONS),
    }
