"""BV v3t-v3v: finite FIFO ACK rank in grants, not universal time fairness."""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import (
    require, runtime_modules_bound, snapshot, source_pins,
)
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources
from spk_bv_research.link_pressure_v0u import ARMS, _arm
from spk_bv_research.actor_service_gap_integration_v3qrs import (
    _run_actor, CAPACITIES, POLICIES, QUOTAS, NULLS,
)
from spk_backvalidation_v2.derived_native_fork_v2g import read_pinned_source
from spk_backvalidation_v2.derived_grant_rank_certificate_v3t import audit_grant_rank

SCHEMA = 'spk-bv-finite-global-ACK-FIFO-grant-rank-conditional-certificate/v3t-v3v'
STATUS = 'DERIVED_SOURCE_FIFO_GRANT_RANK_EXACT_NO_NATIVE_TICK_DEADLINE'
CONTRACT = 'V3T_V3V_SIGNED_V3QRS_PREDECESSOR_ONLY'
PREDECESSOR_SHA = 'fa05758472994887ce55910d4796553d7964cf061ed5df283b305488636c946a'
NEW_SCHEDULES = (
    ('eight_front_back', (1, 2, 3, 4, 25, 26, 27, 28)),
    ('eight_nine_gap', (1, 2, 3, 11, 12, 20, 21, 29)),
    ('eight_late_compressed', (9, 10, 11, 12, 13, 14, 15, 16)),
)
EXCLUSIONS = (
    'FIFO_rank_in_observed_source_grants_is_not_finite_native_tick_liveness',
    'no_positive_lower_bound_on_future_native_ACK_grant_rate',
    'source_pending_due_before_horizon_is_censoring_not_negative_judgment',
    'post_native_source_delivery_does_not_count_as_native_ready',
    'source_FIFO_prefix_does_not_prove_actor_native_learning',
    'source_address_provenance_is_not_cryptographic_identity',
    'derived_ACK_first_or_bounded_turns_is_not_a_frozen_native_actor_policy',
    'no_native_per_actor_deadline_without_an_explicit_service_rate_contract',
)


def validate_v3qrs(prev, raw):
    t = prev.get('actor_progress_totals') if type(prev) is dict else None
    require(type(prev) is dict and type(raw) is bytes and canon(prev) == raw and
            sha256(raw).hexdigest() == PREDECESSOR_SHA and
            prev.get('schema') ==
              'spk-bv-source-actor-specific-ACK-progress-counterexample/v3q-v3s' and
            prev.get('status') ==
              'DERIVED_ACTOR_SPECIFIC_READY_ACK_CUSTODY_PEER_PROGRESS_NO_NATIVE_FAIRNESS' and
            prev.get('reference_v3nop_sha256') ==
              'bbfd059007f2b8c18c4833b207859c277ff04648fa076246085e215470000f94' and
            prev.get('new_original_native_runs') == 18 and
            prev.get('new_derived_actor_runs') == 72 and
            prev.get('new_causal_null_runs') == 36 and
            type(t) is dict and
            t.get('native_original_runs') == 18 and
            t.get('derived_actor_runs') == 72 and
            t.get('causal_null_runs') == 36 and
            t.get('source_delivered') == 1152 and
            t.get('native_inline_ACKs') == 131 and
            t.get('native_ready_actor_ticks') == 3928 and
            t.get('native_missed_actor_ticks') == 3797 and
            t.get('source_peer_progress_actor_misses') == 71 and
            t.get('contexts_with_global_progress_peer_miss') == 47 and
            t.get('maximum_actor_ready_miss_streak') == 37 and
            prev.get('source_per_actor_ACK_custody_verified') is True and
            prev.get('aggregate_ACK_progress_insufficient_for_actor_liveness') is True and
            prev.get('full_original_native_result_projection_preserved') is True and
            prev.get('native_individual_actor_deadline_proven') is False and
            prev.get('native_learning_observed') is False and
            prev.get('native_operator_updates') == 0 and
            prev.get('next_gate') ==
              'BLOCKED_NATIVE_PER_ACTOR_FAIR_SCHEDULING_AND_SERVICE_RATE_CONTRACT' and
            type(prev.get('source_matrix')) is list and
            len(prev['source_matrix']) == 3,
            'v3t-v3v signed v3qrs predecessor altered or incomplete')
    return True


def experiment(prev, raw, *, root: Path, fixture_fn, native_executor, plan_type):
    validate_v3qrs(prev, raw)
    root = root.resolve(strict=True)
    pins, arch, source = source_pins(root), read_pinned_sources(root), read_pinned_source(root)
    runtime_modules_bound(root, native_executor, fixture_fn, plan_type)
    prior_ticks = {tuple(row['source_external_ticks'])
                   for row in prev['source_matrix']}
    totals = dict.fromkeys((
        'new_original_native_runs', 'new_derived_FIFO_rank_runs',
        'new_causal_null_runs', 'full_original_native_projection_cells',
        'source_native_grant_ticks', 'source_native_grant_units',
        'source_native_eligible_controls', 'served_exact_rank_certificates',
        'censored_rank_below_threshold_certificates',
        'post_native_deliveries_excluded',
        'global_grant_with_waiting_other_actor_ticks',
        'sum_due_rank_serviced', 'sum_due_rank_censored',
        'context_with_peer_waiting_and_global_grant'), 0)
    totals['maximum_due_rank'] = 0
    matrix, exemplars = [], []
    nulls = {'source_runs': 0, 'zero_ACKs': 0,
             'zero_absence_certificates': 0, 'exact_native_projection': 0}
    for label, ticks in NEW_SCHEDULES:
        case, fabric, plans = fixture_fn(ticks=ticks)
        require(tuple(e.timestamp for e in case.events) == ticks and
                len(ticks) == 8 and max(ticks) <= 32 and ticks[0] <= 16 and
                all(e.node_id == 'A' and e.channel == 0 for e in case.events) and
                ticks not in prior_ticks,
                'v3t source episode not admitted or repeated from v3qrs')
        modes = []
        for mode, enabled, priority in ARMS:
            capacities = []
            for cap in CAPACITIES:
                altered = (plans[0], replace(plans[1], fabric_slots_per_tick=cap),
                           plans[2], plans[3])
                data = case, fabric, altered
                digest = snapshot(data)
                captured = {}

                def capture(*args, **kwargs):
                    captured['native'] = native_executor(*args, **kwargs)
                    return captured['native']

                native_receipt = _arm(capture, plan_type, case, fabric, altered,
                    'v3t-original-'+label+'-'+mode+'-'+str(cap),
                    enabled, priority, digest, data)
                native = captured['native']
                totals['new_original_native_runs'] += 1
                policies = {}
                for policy in POLICIES:
                    quotas = {}
                    for quota in QUOTAS:
                        (acks, paid, probes, ledger, summary, receiver,
                         records, projected) = _run_actor(
                            source, native_executor, plan_type, case, fabric,
                            altered, enabled, priority, digest, data,
                            quota=quota, policy=policy)
                        audit = audit_grant_rank(acks, paid, probes, ledger,
                            summary, receiver, records, policy=policy,
                            global_quota=quota, native_PE_budget=cap)
                        require(projected == native and
                                audit['source_FIFO_prefix_for_observed_context'] and
                                audit['source_conditional_grant_rank_verified'] and
                                not audit['future_grant_arrival_or_tick_deadline_proven'],
                                'v3t-v3v native projection or local FIFO grant rank failed')
                        totals['new_derived_FIFO_rank_runs'] += 1
                        totals['full_original_native_projection_cells'] += 1
                        c = audit['totals']
                        for source_key, aggregate_key in (
                                ('source_grant_ticks', 'source_native_grant_ticks'),
                                ('source_grant_units', 'source_native_grant_units'),
                                ('eligible_delivered_native_controls',
                                 'source_native_eligible_controls'),
                                ('conditional_exact_rank_serviced',
                                 'served_exact_rank_certificates'),
                                ('conditional_rank_not_reached_censored',
                                 'censored_rank_below_threshold_certificates'),
                                ('post_native_deliveries_not_native_ready',
                                 'post_native_deliveries_excluded'),
                                ('global_grant_with_other_actor_waiting_ticks',
                                 'global_grant_with_waiting_other_actor_ticks'),
                                ('sum_due_rank_serviced', 'sum_due_rank_serviced'),
                                ('sum_due_rank_censored', 'sum_due_rank_censored')):
                            totals[aggregate_key] += c[source_key]
                        totals['maximum_due_rank'] = max(
                            totals['maximum_due_rank'], c['maximum_due_rank'])
                        totals['context_with_peer_waiting_and_global_grant'] += int(
                            c['global_grant_with_other_actor_waiting_ticks'] > 0)
                        if (audit['first_global_grant_with_unserviced_peer'] and
                                len(exemplars) < 18):
                            exemplars.append({'schedule': label, 'native_mode': mode,
                                'native_PE_budget': cap, 'policy': policy,
                                'global_ACK_quota': quota,
                                'original_native_result_sha256': native_receipt[
                                    'whole_result_sha256'],
                                'source_journal_sha256': sha256(canon(acks)).hexdigest(),
                                'source_fifo_prefix': audit[
                                    'first_global_grant_with_unserviced_peer'],
                                'rank_certificates': audit['exact_grant_rank_witnesses']})
                        quotas[str(quota)] = {
                            'full_original_native_result_exact': True,
                            'source_ACK_journal_sha256': sha256(canon(acks)).hexdigest(),
                            'rank_audit': audit,
                        }
                    policies[policy] = quotas
                for intervention in NULLS:
                    ack, paid, _, _, summary, receiver, _, projected = _run_actor(
                        source, native_executor, plan_type, case, fabric,
                        altered, enabled, priority, digest, data,
                        quota=2, policy='ACK-first', intervention=intervention)
                    require(projected == native and not ack and not paid and
                            summary['absence_certificates'] == 0 and
                            receiver['absence_certificates'] == 0,
                            'v3v causal null fabricated source ACK/silence certificate')
                    nulls['source_runs'] += 1
                    nulls['zero_ACKs'] += 1
                    nulls['zero_absence_certificates'] += 1
                    nulls['exact_native_projection'] += 1
                    totals['new_causal_null_runs'] += 1
                capacities.append({'native_PE_capacity': cap,
                    'original_native_sha256': native_receipt['whole_result_sha256'],
                    'derived_policies': policies})
                require(snapshot(data) == digest,
                        'v3t source-owned workload was mutated during replay')
            modes.append({'mode': mode, 'capacities': capacities})
        matrix.append({'schedule': label, 'source_external_ticks': list(ticks),
                       'modes': modes})
    require(totals['new_original_native_runs'] == 18 and
            totals['new_derived_FIFO_rank_runs'] ==
                totals['full_original_native_projection_cells'] == 72 and
            totals['new_causal_null_runs'] ==
                nulls['source_runs'] == nulls['zero_ACKs'] ==
                nulls['zero_absence_certificates'] ==
                nulls['exact_native_projection'] == 36 and
            totals['source_native_grant_units'] ==
                totals['served_exact_rank_certificates'] and
            totals['source_native_eligible_controls'] ==
                totals['served_exact_rank_certificates'] +
                totals['censored_rank_below_threshold_certificates'] and
            totals['source_native_grant_units'] > 0 and
            totals['censored_rank_below_threshold_certificates'] > 0 and
            totals['global_grant_with_waiting_other_actor_ticks'] > 0 and
            read_pinned_source(root) == source and
            read_pinned_sources(root) == arch and source_pins(root) == pins,
            'v3t-v3v missing source rank, censoring or causal-null closure')
    return {'source_matrix': matrix, 'grant_rank_totals': totals,
            'strict_fifo_peer_progress_witnesses': exemplars,
            'causal_nulls': nulls,
            'exact_source_FIFO_rank_in_grant_units': True,
            'full_original_native_projection_preserved': True,
            'frozen_pinned_source_preserved': True}


def build_report(prev, raw, result=None):
    validate_v3qrs(prev, raw)
    require(result is None or (
        result['grant_rank_totals']['new_original_native_runs'] == 18 and
        result['grant_rank_totals']['new_derived_FIFO_rank_runs'] == 72 and
        result['causal_nulls']['source_runs'] == 36 and
        result['exact_source_FIFO_rank_in_grant_units'] and
        result['full_original_native_projection_preserved'] and
        result['frozen_pinned_source_preserved']),
        'v3t-v3v source grant rank/replay completeness missing')
    totals = result['grant_rank_totals'] if result else None
    return {
        'schema': SCHEMA, 'status': STATUS if result else CONTRACT,
        'reference_v3qrs_sha256': sha256(raw).hexdigest(),
        'research_stages': [
            'v3t-source-ready-judgment-global-FIFO-grant-prefix-verifier',
            'v3u-conditional-exact-ordinal-rank-of-service-in-real-grant-units',
            'v3v-three-new-source-admitted-schedules-causal-nulls-native-censoring',
        ],
        'source_matrix': result['source_matrix'] if result else None,
        'grant_rank_totals': totals,
        'strict_fifo_peer_progress_witnesses': result[
            'strict_fifo_peer_progress_witnesses'] if result else None,
        'causal_nulls': result['causal_nulls'] if result else None,
        'new_original_native_runs': totals['new_original_native_runs'] if totals else 0,
        'new_derived_rank_runs': totals['new_derived_FIFO_rank_runs'] if totals else 0,
        'new_causal_null_runs': totals['new_causal_null_runs'] if totals else 0,
        'finite_source_FIFO_and_exact_grant_rank_verified': bool(result),
        'full_original_native_projection_preserved': bool(result),
        'universal_native_tick_deadline_proven': False,
        'native_actor_learning_observed': False,
        'native_operator_updates': 0,
        'claims_excluded': list(EXCLUSIONS),
        'next_gate': 'BLOCKED_NATIVE_PER_ACTOR_MINIMUM_GRANT_RATE_AND_FAIR_SCHEDULER_CONTRACT',
    }
