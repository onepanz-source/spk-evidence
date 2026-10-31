"""v3h-v3j cumulative finite ACK tail capacity, prefixes and cutover.

Exact original-native projection remains required. The tail is a bounded,
separately charged *derived* control service, not frozen native actor intake.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import (
    require, source_pins, runtime_modules_bound, snapshot,
)
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources
from spk_bv_research.link_pressure_v0u import ARMS, _arm
from spk_bv_research.native_veto_attribution_v3efg import ALL_SCHEDULES
from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver, read_pinned_source,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import ReceiverPortV2h
from spk_backvalidation_v2.derived_actor_control_service_v2j import ShadowServicePlanV2j
from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import ActorCreditPlanV2l
from spk_backvalidation_v2.derived_causal_admission_v2o import CausalAdmissionPlanV2o
from spk_backvalidation_v2.derived_actor_queue_fairness_v2v import (
    ActorQueuePlanV2v, DerivedActorQueueFairnessV2v,
    derive_queue_fairness_executor,
)
from spk_backvalidation_v2.derived_ack_tail_envelope_v3h import audit_tail_envelope

SCHEMA = 'spk-bv-native-safe-derived-ACK-tail-opportunity-boundary/v3h-v3j'
STATUS = 'DERIVED_FINITE_ACK_TAIL_CUTOVER_PREFIX_RESOURCE_ENVELOPE_NO_NATIVE_LIVENESS'
CONTRACT = 'V3H_V3J_SIGNED_V3EFG_PREDECESSOR_ONLY'
PREDECESSOR_SHA = '93fd26296492945629f0d93dfc6fbb2e41f69b6ae8d009813b447db1c1ffc4f3'
EXPLICIT_LIMITS = (0, 1, 2, 4, 8, 16, 32)
QUOTAS = (1, 2)
NULLS = ('zero_credit', 'transport_loss')
EXCLUSIONS = (
    'minimal_tail_horizon_is_observed_for_pinned_27_contexts_not_a_global_deadline',
    'quota_one_vs_two_is_a_derived_service_model_not_native_policy',
    'native_ready_veto_can_postpone_first_safe_tail_opportunity_without_bound',
    'tail_off_pending_or_transport_loss_is_not_a_negative_judgment_or_silence_proof',
    'forward_payload_parity_does_not_grant_native_actor_learning',
    'finite_tail_prefix_and_resource_paid_receipts_do_not_prove_starvation_freedom',
    'no_hardware_energy_cross_node_authenticity_or_mesh_transport_claim',
)


def validate_v3efg(prev, raw):
    require(type(prev) is dict and type(raw) is bytes and canon(prev) == raw and
            sha256(raw).hexdigest() == PREDECESSOR_SHA,
            'v3h-v3j noncanonical or altered signed v3efg predecessor')
    require(prev.get('schema') ==
            'spk-bv-native-ready-guard-factorial-wait-tail-closure/v3e-v3g' and
            prev.get('status') ==
            'DERIVED_NATIVE_GUARD_FACTORIAL_WAIT_OVERLAP_NO_UNIVERSAL_ACK_DEADLINE' and
            prev.get('reference_v3bcd_sha256') ==
            'd347de60d14893380c5433993d2c6aefee46118bf6dbff6da13198d272ac4b90' and
            prev.get('new_native_runs') == 27 and
            prev.get('new_derived_policy_runs') == 324 and
            prev.get('new_null_runs') == 54 and
            prev.get('new_tail_off_runs') == 27 and
            prev.get('factorial_contrasts', {}).get('cells') == 81 and
            prev.get('tail_disabled_observations', {}).get('delivered_unacked') == 266 and
            prev.get('finite_source_guard_wait_overlap_measured') is True and
            prev.get('strict_full_native_projection_preserved') is True and
            prev.get('universal_ACK_deadline_or_native_learning_proven') is False and
            prev.get('native_operator_updates') == 0 and
            prev.get('next_gate') ==
            'BLOCKED_GLOBAL_ACK_PROGRESS_WITHOUT_NATIVE_SERVICE_GUARANTEE',
            'v3h-v3j predecessor result/exclusions altered')
    matrix = prev.get('source_matrix')
    require(type(matrix) is list and len(matrix) == len(ALL_SCHEDULES) and
            [row.get('schedule') for row in matrix] ==
            [name for name, _ in ALL_SCHEDULES] and
            all([mode.get('mode') for mode in row.get('modes', ())] ==
                [name for name, _, _ in ARMS]
                for row in matrix),
            'v3h-v3j predecessor signed source context matrix incomplete')
    return True


def _run_budget(source, native_executor, plan_type, case, fabric, plans,
                enabled, priority, digest, data, *, tail_limit, quota,
                intervention='normal'):
    require(type(tail_limit) is int and 0 <= tail_limit <= 32 and
            type(quota) is int and quota in QUOTAS and
            intervention in ('normal', *NULLS),
            'v3h invalid source bounded tail/ACK quota/intervention')
    port = ReceiverPortV2h(
        latency=2, accept=(lambda _: False)
        if intervention == 'transport_loss' else None)
    actor = DerivedActorQueueFairnessV2v(
        port, queue_plan=ActorQueuePlanV2v('bounded-turns'),
        admission_plan=CausalAdmissionPlanV2o(True, True),
        service_plan=ShadowServicePlanV2j(max_per_tick=quota,
                                           max_tail_ticks=tail_limit),
        credit_plan=(ActorCreditPlanV2l(max_abs_credit=0)
                     if intervention == 'zero_credit' else ActorCreditPlanV2l()))
    observer = CallsiteObserver()
    executor, _, semantic, resources = derive_queue_fairness_executor(
        source, native_executor, port, actor, observer)
    captured = {}

    def run(*args, **kwargs):
        captured['derived'] = executor(*args, **kwargs)
        captured['projected'] = actor.project_original_native_result(
            captured['derived'])
        return captured['projected']

    _arm(run, plan_type, case, fabric, plans,
         'v3h-tail-'+str(tail_limit)+'-quota-'+str(quota),
         enabled, priority, digest, data)
    summary, port_summary = actor.summary(), port.summary()
    ACKs, paid = actor.credit_journal(), actor.concurrent_journal()
    witness = audit_tail_envelope(ACKs, paid, actor.queue_fairness_probes(),
        summary, port_summary, tail_limit=tail_limit, per_tick_quota=quota)
    require(semantic == (('batch', 194), ('clock', 125), ('emission', 217),
                         ('ingress', 136)) and resources == (158, 296, 307) and
            not observer.overflow and not observer.sink_failed and
            observer.counts()['_admit'] == 1 and
            summary['within_original_native_plan_capacity'] and
            summary['frozen_actor_state_changed'] is False and
            summary['native_operator_updates'] == 0 and
            summary['absence_certificates'] == 0 and
            summary['concurrent_consumer_PE_units'] == len(paid) and
            summary['concurrent_consumer_memory_units'] == 2*len(paid) and
            witness['complete_delivered_control_service'] is
                (witness['delivered_pending_not_negative'] == 0),
            'v3h source-derived native resource/consumer/ACK custody drift')
    return ACKs, paid, witness, captured['projected'], summary, port_summary


def _prefix_from_full(full, native_last, cap):
    return [ack for ack in full if ack['resource_phase'] == 'native-slack' or
            ack['serviced_tick'] <= native_last+cap]


def experiment(prev, raw, *, root: Path, fixture_fn, native_executor, plan_type):
    validate_v3efg(prev, raw)
    root = root.resolve(strict=True)
    pins = source_pins(root)
    arch = read_pinned_sources(root)
    source = read_pinned_source(root)
    runtime_modules_bound(root, native_executor, fixture_fn, plan_type)
    totals = {str(q): {
        'contexts': 0, 'full_service_contexts_at_32': 0,
        'at_zero_tail_incomplete_contexts': 0,
        'prefix_comparisons': 0, 'prefix_identical': 0,
        'ACK_capacity_monotone_comparisons': 0,
        'capacity_monotone_passes': 0,
        'minimal_cutover_validated': 0,
        'max_tail_ticks_needed': 0,
        'sum_tail_ticks_needed': 0,
        'sum_tail_lower_bound_ticks': 0,
        'no_late_tail_due_contexts': 0,
        'lower_bound_tight_contexts': 0,
        'source_delivered': 0,
        'source_full_ACKs': 0,
        'budget_runs': 0,
    } for q in QUOTAS}
    nulls = {name: {'runs': 0, 'native_exact': 0, 'ACKs': 0,
                    'paid_consumer_receipts': 0, 'no_negative_proof': 0}
             for name in NULLS}
    rows = []
    new_derived_budget_runs = 0
    for label, ticks in ALL_SCHEDULES:
        case, fabric, plans = fixture_fn(ticks=ticks)
        require(tuple(e.timestamp for e in case.events) == ticks and
                len(ticks) <= 8 and
                all(e.node_id == 'A' and e.channel == 0 for e in case.events),
                'v3h forged or unadmitted original source episode')
        altered = (plans[0], replace(plans[1], fabric_slots_per_tick=2),
                   plans[2], plans[3])
        data = (case, fabric, altered)
        digest = snapshot(data)
        modes = []
        for mode, enabled, priority in ARMS:
            captured = {}

            def capture(*args, **kwargs):
                captured['native'] = native_executor(*args, **kwargs)
                return captured['native']

            original = _arm(capture, plan_type, case, fabric, altered,
                'v3h-original-native-'+label+'-'+mode,
                enabled, priority, digest, data)
            native = captured['native']
            quota_rows = {}
            for quota in QUOTAS:
                t = totals[str(quota)]
                full, full_paid, full_witness, full_projected, _, _ = (
                    _run_budget(source, native_executor, plan_type,
                                case, fabric, altered, enabled, priority,
                                digest, data, tail_limit=32, quota=quota))
                require(full_projected == native and
                        full_witness['complete_delivered_control_service'] and
                        len(full) == len(full_paid),
                        'v3h 32-tick source tail failed to drain given workload')
                end = full_witness['source_native_last_tick']
                tail = [a for a in full if a['resource_phase'] == 'post-native-tail']
                H = max((a['serviced_tick']-end for a in tail), default=0)
                counts = Counter(a['actor'] for a in tail)
                lower_bound = max((len(tail)+quota-1)//quota,
                                  max(counts.values(), default=0))
                require(0 <= lower_bound <= H <= 32,
                        'v3h source tail finished before resource lower bound')
                limits = sorted(set(EXPLICIT_LIMITS + (H, max(0, H-1))))
                observed = {32: (full, full_paid, full_witness)}
                for cap in limits:
                    if cap != 32:
                        acks, paid, witness, projected, _, _ = _run_budget(
                            source, native_executor, plan_type, case, fabric,
                            altered, enabled, priority, digest, data,
                            tail_limit=cap, quota=quota)
                        require(projected == native,
                                'v3h tail cutoff modified frozen native output')
                        observed[cap] = (acks, paid, witness)
                        new_derived_budget_runs += 1
                    actual, paid, w = observed[cap]
                    prefix = _prefix_from_full(full, end, cap)
                    require(actual == prefix and
                            w['source_native_last_tick'] == end and
                            w['delivered_source_controls'] == len(full) and
                            all(r['due_tick'] <= r['serviced_tick'] for r in actual),
                            'v3i tail capacity rewrote earlier source-owned ACK chain')
                    t['prefix_comparisons'] += 1
                    t['prefix_identical'] += 1
                new_derived_budget_runs += 1  # full / 32 included
                for before, after in zip(limits, limits[1:]):
                    require(len(observed[before][0]) <= len(observed[after][0]),
                            'v3i larger real tail budget removed a source ACK')
                    t['ACK_capacity_monotone_comparisons'] += 1
                    t['capacity_monotone_passes'] += 1
                require(observed[H][2]['complete_delivered_control_service'] and
                        (H == 0 or not observed[H-1][2][
                            'complete_delivered_control_service']) and
                        observed[0][2]['tail_ACKs'] == 0 and
                        observed[0][2]['source_ACK_count'] <= len(full),
                        'v3j finite source tail cutover is not minimal/exact')
                t['contexts'] += 1
                t['full_service_contexts_at_32'] += 1
                t['at_zero_tail_incomplete_contexts'] += int(
                    not observed[0][2]['complete_delivered_control_service'])
                t['minimal_cutover_validated'] += 1
                t['max_tail_ticks_needed'] = max(t['max_tail_ticks_needed'], H)
                t['sum_tail_ticks_needed'] += H
                t['sum_tail_lower_bound_ticks'] += lower_bound
                t['no_late_tail_due_contexts'] += int(
                    full_witness['tail_due_after_first_tail_tick'] == 0)
                t['lower_bound_tight_contexts'] += int(H == lower_bound)
                t['source_delivered'] += full_witness['delivered_source_controls']
                t['source_full_ACKs'] += len(full)
                t['budget_runs'] += len(limits)
                quota_rows[str(quota)] = {
                    'full_native_equal': True,
                    'original_native_last_tick': end,
                    'delivered_source_controls': len(full),
                    'tail_ACKs': len(tail),
                    'per_actor_tail_ACKs': dict(sorted(counts.items())),
                    'source_tail_ticks_needed': H,
                    'resource_lower_bound_tail_ticks': lower_bound,
                    'first_tail_due_condition_holds':
                        full_witness['tail_due_after_first_tail_tick'] == 0,
                    'exact_cutover_at_H_and_not_H_minus_one': True,
                    'budget_results': [{
                        'tail_limit_ticks': cap,
                        'ACK_count': len(observed[cap][0]),
                        'paid_consumer_receipts': len(observed[cap][1]),
                        'unconsumed_delivered': observed[cap][2][
                            'delivered_pending_not_negative'],
                        'tail_grants': observed[cap][2]['tail_ACKs'],
                        'ACK_journal_sha256': sha256(canon(observed[cap][0])).hexdigest(),
                        'native_exact': True,
                    } for cap in limits],
                }
            for intervention in NULLS:
                acks, paid, witness, projected, _, port = _run_budget(
                    source, native_executor, plan_type, case, fabric,
                    altered, enabled, priority, digest, data,
                    tail_limit=32, quota=2, intervention=intervention)
                require(projected == native and not acks and not paid and
                        port['absence_certificates'] == 0 and
                        (not witness['complete_delivered_control_service']
                         if intervention == 'zero_credit' else
                         witness['delivered_source_controls'] == 0),
                        'v3j causal null minted control ACK or silence certificate')
                n = nulls[intervention]
                n['runs'] += 1
                n['native_exact'] += 1
                n['no_negative_proof'] += 1
            modes.append({'mode': mode,
                          'source_native_sha256': original['whole_result_sha256'],
                          'quotas': quota_rows})
        rows.append({'schedule': label, 'source_external_ticks': list(ticks),
                     'modes': modes})
        require(snapshot((case, fabric, altered)) == digest,
                'v3h source native fixture mutated during tail experiments')
    cells = len(ALL_SCHEDULES)*len(ARMS)
    require(all(t['contexts'] == cells and
                t['full_service_contexts_at_32'] == cells and
                t['minimal_cutover_validated'] == cells and
                t['prefix_identical'] == t['prefix_comparisons'] and
                t['capacity_monotone_passes'] == t[
                    'ACK_capacity_monotone_comparisons'] and
                t['source_delivered'] == t['source_full_ACKs'] and
                t['at_zero_tail_incomplete_contexts'] == cells and
                t['lower_bound_tight_contexts'] == cells
                for t in totals.values()) and
            all(n['runs'] == n['native_exact'] == n['no_negative_proof'] == cells and
                n['ACKs'] == n['paid_consumer_receipts'] == 0
                for n in nulls.values()) and
            new_derived_budget_runs == sum(t['budget_runs']
                                          for t in totals.values()) and
            read_pinned_source(root) == source and source_pins(root) == pins and
            read_pinned_sources(root) == arch,
            'v3h-v3j finite source opportunity/cutover/causal null closure failed')
    return {
        'source_matrix': rows,
        'per_global_ACK_tick_quota_totals': totals,
        'causal_null_totals': nulls,
        'new_native_runs': cells,
        'new_derived_budget_runs': new_derived_budget_runs,
        'new_causal_null_runs': cells*len(NULLS),
        'total_source_tail_prefix_comparisons': sum(t['prefix_comparisons']
                                                   for t in totals.values()),
        'total_source_capacity_monotonicity_comparisons': sum(
            t['ACK_capacity_monotone_comparisons'] for t in totals.values()),
        'exact_finite_cutovers': sum(t['minimal_cutover_validated']
                                    for t in totals.values()),
        'frozen_source_pins_preserved': True,
    }


def build_report(prev, raw, result=None):
    validate_v3efg(prev, raw)
    require(result is None or (
        result['frozen_source_pins_preserved'] and
        result['new_native_runs'] == 27 and
        result['new_causal_null_runs'] == 54 and
        result['exact_finite_cutovers'] == 54 and
        all(x['lower_bound_tight_contexts'] == 27
            for x in result['per_global_ACK_tick_quota_totals'].values()) and
        result['total_source_tail_prefix_comparisons'] > 54 and
        result['new_derived_budget_runs'] > 54),
        'v3h-v3j missing real derived tail/causal source evidence')
    return {
        'schema': SCHEMA,
        'status': STATUS if result else CONTRACT,
        'reference_v3efg_sha256': sha256(raw).hexdigest(),
        'cumulative_research_stages': [
            'v3h-source-native-safe-derived-tail-1-vs-2-global-ACK-quotas',
            'v3i-finite-tail-ACK-journal-prefix-and-capacity-monotonicity',
            'v3j-minimum-source-tail-cutover-H-versus-H-minus-one-and-causal-null',
        ],
        'new_native_runs': result['new_native_runs'] if result else 0,
        'new_derived_budget_runs': result['new_derived_budget_runs'] if result else 0,
        'new_causal_null_runs': result['new_causal_null_runs'] if result else 0,
        'total_source_tail_prefix_comparisons':
            result['total_source_tail_prefix_comparisons'] if result else 0,
        'total_source_capacity_monotonicity_comparisons':
            result['total_source_capacity_monotonicity_comparisons'] if result else 0,
        'exact_finite_cutovers': result['exact_finite_cutovers'] if result else 0,
        'per_global_ACK_tick_quota_totals':
            result['per_global_ACK_tick_quota_totals'] if result else None,
        'causal_null_totals': result['causal_null_totals'] if result else None,
        'source_matrix': result['source_matrix'] if result else None,
        'source_finite_minimal_tail_service_witness': bool(result),
        'full_strict_native_result_projection_preserved': bool(result),
        'universal_ACK_deadline_or_native_learning_proven': False,
        'native_operator_updates': 0,
        'next_gate': 'BLOCKED_NATIVE_GUARANTEED_SERVICE_OPPORTUNITY_AND_ACTOR_LEARNING',
        'claims_excluded': list(EXCLUSIONS),
    }
