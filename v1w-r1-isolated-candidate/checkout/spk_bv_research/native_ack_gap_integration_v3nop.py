"""BV v3n-v3p: finite native-ready ACK gaps and bounded-proof boundary.

Three *new, admitted* eight-event schedules are replayed with the frozen
native executor.  Neither a finite trace nor an abstract future extension is
relabelled as a universal native service or learning guarantee.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from search.spk_bv_v0e_live_evidence import fixture
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import (
    require, runtime_modules_bound, snapshot, source_pins,
)
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources
from spk_bv_research.link_pressure_v0u import ARMS, _arm
from spk_bv_research.native_ack_opportunity_integration_v3klm import (
    PREDECESSOR_SHA as V3HIJ_SHA, _run_source,
)
from spk_backvalidation_v2.derived_native_fork_v2g import read_pinned_source
from spk_backvalidation_v2.derived_ack_wait_gap_v3n import (
    MISS_CLASSES, THRESHOLDS, audit_ready_gap,
)

SCHEMA = 'spk-bv-source-native-ready-ACK-gap-and-proof-boundary/v3n-v3p'
STATUS = 'DERIVED_FINITE_READY_ACK_WAIT_GAP_SOURCE_DISCRIMINATOR_NO_GLOBAL_DEADLINE'
CONTRACT = 'V3N_V3P_SIGNED_V3KLM_PREDECESSOR_ONLY'
PREDECESSOR_SHA = '6fe69d43c3e4ef75e7162ef053903780ad7a470b9f8603220bee607dba761607'
NEW_SCHEDULES = (
    ('eight_three_gap', (1, 4, 7, 10, 13, 16, 19, 22)),
    ('eight_clusters', (1, 2, 3, 8, 9, 10, 15, 16)),
    ('eight_even', (2, 4, 6, 8, 10, 12, 14, 16)),
)
CAPACITIES = (1, 2)
QUOTAS = (1, 2)
POLICIES = ('ACK-first', 'bounded-turns')
NULLS = ('transport_loss', 'zero_credit')
EXCLUSIONS = (
    'a_finite_ready_ACK_gap_is_not_a_universal_source_scheduler_deadline',
    'individual_actor_credits_cannot_be_bounded_by_aggregate_global_ACK_grants',
    'source_native_horizon_end_is_censoring_not_receiver_silence_or_negative_vote',
    'more_global_quota_need_not_monotonically_reduce_inline_ack_wait',
    'abstract_indistinguishable_future_extensions_are_not_frozen_native_traces',
    'unadmitted_ninth_external_event_cannot_be_used_to_claim_unbounded_native_starvation',
    'no_native_actor_learning_or_universal_liveness_contract',
)


def validate_v3klm(prev, raw):
    require(type(prev) is dict and type(raw) is bytes and canon(prev) == raw and
            sha256(raw).hexdigest() == PREDECESSOR_SHA and
            prev.get('schema') ==
              'spk-bv-finite-conditional-native-ACK-opportunity-discriminator/v3k-v3m' and
            prev.get('status') ==
              'DERIVED_NATIVE_ACK_OPPORTUNITY_RESOURCE_AND_QUEUE_CONDITIONAL_NO_LIVENESS' and
            prev.get('reference_v3hij_sha256') == V3HIJ_SHA and
            prev.get('new_original_native_runs') == 54 and
            prev.get('new_derived_policy_runs') == 216 and
            prev.get('new_causal_null_runs') == 108 and
            prev.get('sufficient_source_opportunities') == 356 and
            prev.get('unsafe_weak_no_veto_opportunities') == 44 and
            prev.get('strict_full_original_native_projection_preserved') is True and
            prev.get('source_conditional_ACK_opportunity_observed') is True and
            prev.get('universal_ACK_liveness_or_native_learning_proven') is False and
            prev.get('native_operator_updates') == 0 and
            prev.get('next_gate') ==
              'BLOCKED_GLOBAL_NATIVE_OPPORTUNITY_RATE_OR_FAIR_SCHEDULER_CONTRACT',
            'v3n-v3p noncanonical/changed signed v3klm predecessor')
    mat = prev.get('source_matrix')
    contrasts = prev.get('policy_and_global_resource_contrasts')
    require(type(mat) is list and len(mat) == 9 and
            type(contrasts) is dict and
            contrasts.get('policy_pairs') == 108 and
            contrasts.get('quota_pairs') == 108 and
            contrasts.get('normal_native_projection_exact') == 216 and
            contrasts.get('higher_quota_fewer_inline') == 7 and
            type(prev.get('nonmonotone_inline_quota_witnesses')) is list and
            len(prev['nonmonotone_inline_quota_witnesses']) == 7 and
            all(type(row) is dict and type(row.get('modes')) is list and
                len(row['modes']) == 3 for row in mat),
            'v3n-v3p signed predecessor source/matrix proof boundary drift')
    return True


def _empty():
    return {'contexts': 0, 'native_ticks': 0, 'ready_ticks': 0,
            'ready_miss_ticks': 0, 'ready_grant_ticks': 0, 'ACKs': 0,
            'paid_consumer_receipts': 0, 'pending_not_negative': 0,
            'native_veto_miss_ticks': 0, 'consumer_first_miss_ticks': 0,
            'ACK_first_resource_unproven_miss_ticks': 0,
            'censored_gap_episodes': 0,
            'max_consecutive_ready_miss_ticks': 0}


def experiment(prev, raw, *, root: Path, fixture_fn, native_executor, plan_type):
    validate_v3klm(prev, raw)
    root = root.resolve(strict=True)
    pins, arch, source = source_pins(root), read_pinned_sources(root), read_pinned_source(root)
    runtime_modules_bound(root, native_executor, fixture_fn, plan_type)
    totals = {str(cap): {policy: {str(q): _empty() for q in QUOTAS}
                         for policy in POLICIES} for cap in CAPACITIES}
    thresholds = {str(t): 0 for t in THRESHOLDS}
    rows, long_gap_witnesses, quota_inversions = [], [], []
    nulls = {'runs': 0, 'strict_native_parity': 0,
             'ACKs': 0, 'consumer_receipts': 0, 'absence_certificates': 0}
    comparisons = {'policy_pairs': 0, 'ACK_first_inline_not_less': 0,
                   'quota_pairs': 0, 'higher_quota_inline_less': 0,
                   'higher_quota_worsens_max_ready_gap': 0,
                   'strict_native_parity_cells': 0}
    for label, ticks in NEW_SCHEDULES:
        case, fabric, plans = fixture_fn(ticks=ticks)
        require(tuple(e.timestamp for e in case.events) == ticks and
                all(e.node_id == 'A' and e.channel == 0 for e in case.events) and
                len(ticks) == 8 and max(ticks) <= 32 and
                label not in [m.get('schedule') for m in prev['source_matrix']] and
                list(ticks) not in [m.get('source_external_ticks')
                                    for m in prev['source_matrix']],
                'v3n new schedule not source admitted or reuses old cell')
        source_modes = []
        for mode, enabled, priority in ARMS:
            caps = []
            for cap in CAPACITIES:
                altered = (plans[0], replace(plans[1], fabric_slots_per_tick=cap),
                           plans[2], plans[3])
                data = (case, fabric, altered)
                digest = snapshot(data)
                captured = {}

                def native_capture(*args, **kwargs):
                    captured['native'] = native_executor(*args, **kwargs)
                    return captured['native']

                source_native = _arm(native_capture, plan_type, case, fabric,
                    altered, 'v3n-native-'+label+'-'+mode+'-'+str(cap),
                    enabled, priority, digest, data)
                native = captured['native']
                pol = {}
                for policy in POLICIES:
                    quota_rows = {}
                    for quota in QUOTAS:
                        ack, paid, probes, ledger, summary, receiver, projected = (
                            _run_source(source, native_executor, plan_type,
                                case, fabric, altered, enabled, priority, digest,
                                data, quota=quota, policy=policy))
                        audit = audit_ready_gap(
                            ack, paid, probes, ledger, summary, receiver,
                            policy=policy, global_quota=quota,
                            native_PE_budget=cap)
                        require(projected == native and
                                audit['conditional_progress_verified'] and
                                not audit['per_actor_deadline_inferred'] and
                                not audit['native_future_opportunity_rate_inferred'],
                                'v3n native projection or exact ready gap rejected')
                        c = audit['totals']
                        dest = totals[str(cap)][policy][str(quota)]
                        dest['contexts'] += 1
                        for source_key, dest_key in (
                                ('native_ticks', 'native_ticks'),
                                ('ready_ticks', 'ready_ticks'),
                                ('ready_miss_ticks', 'ready_miss_ticks'),
                                ('ready_grant_ticks', 'ready_grant_ticks'),
                                ('grant_units', 'ACKs'),
                                ('source_pending_not_negative', 'pending_not_negative'),
                                ('native_veto_miss_ticks', 'native_veto_miss_ticks'),
                                ('consumer_first_miss_ticks', 'consumer_first_miss_ticks'),
                                ('ACK_first_resource_unproven_miss_ticks',
                                 'ACK_first_resource_unproven_miss_ticks'),
                                ('censored_at_native_end', 'censored_gap_episodes')):
                            dest[dest_key] += c[source_key]
                        dest['paid_consumer_receipts'] += len(paid)
                        dest['max_consecutive_ready_miss_ticks'] = max(
                            dest['max_consecutive_ready_miss_ticks'],
                            c['max_consecutive_ready_miss_ticks'])
                        for bound, witnessed in c['miss_thresholds_witnessed'].items():
                            thresholds[bound] += int(witnessed)
                        if c['max_consecutive_ready_miss_ticks'] >= 16:
                            longest = max(audit['miss_episodes'],
                                          key=lambda episode: episode['length'])
                            long_gap_witnesses.append({
                                'schedule': label, 'mode': mode, 'native_PE_capacity': cap,
                                'policy': policy, 'global_ACK_quota': quota,
                                'source_native_sha256': source_native['whole_result_sha256'],
                                'source_ACK_journal_sha256': sha256(canon(ack)).hexdigest(),
                                'source_delivered': receiver['control_delivered'],
                                'source_unconsumed_not_negative':
                                    c['source_pending_not_negative'],
                                'ready_gap': longest,
                            })
                        comparisons['strict_native_parity_cells'] += 1
                        quota_rows[str(quota)] = {
                            'full_native_projection_exact': True,
                            'source_ACK_count': len(ack),
                            'source_paid_consumer_count': len(paid),
                            'source_ACK_journal_sha256': sha256(canon(ack)).hexdigest(),
                            'source_gap': audit,
                        }
                    pol[policy] = quota_rows
                for q in QUOTAS:
                    comparisons['policy_pairs'] += 1
                    comparisons['ACK_first_inline_not_less'] += int(
                        pol['ACK-first'][str(q)]['source_ACK_count'] >=
                        pol['bounded-turns'][str(q)]['source_ACK_count'])
                for policy in POLICIES:
                    comparisons['quota_pairs'] += 1
                    lo, hi = (pol[policy][str(q)] for q in QUOTAS)
                    comparisons['higher_quota_inline_less'] += int(
                        hi['source_ACK_count'] < lo['source_ACK_count'])
                    comparisons['higher_quota_worsens_max_ready_gap'] += int(
                        hi['source_gap']['totals']['max_consecutive_ready_miss_ticks'] >
                        lo['source_gap']['totals']['max_consecutive_ready_miss_ticks'])
                    if hi['source_ACK_count'] < lo['source_ACK_count']:
                        quota_inversions.append({
                            'schedule': label, 'mode': mode,
                            'native_PE_capacity': cap, 'policy': policy,
                            'quota_one_ACK_count': lo['source_ACK_count'],
                            'quota_two_ACK_count': hi['source_ACK_count'],
                        })
                for intervention in NULLS:
                    a, paid, _, _, summary, receiver, projected = _run_source(
                        source, native_executor, plan_type, case, fabric,
                        altered, enabled, priority, digest, data, quota=2,
                        policy='ACK-first', intervention=intervention)
                    require(projected == native and not a and not paid and
                            receiver['absence_certificates'] == 0 and
                            summary['derived_control_tail_grants'] == 0,
                            'v3p transport loss/credit cap null fabricates ACK proof')
                    nulls['runs'] += 1
                    nulls['strict_native_parity'] += 1
                caps.append({'native_PE_capacity': cap,
                    'source_original_result_sha256': source_native['whole_result_sha256'],
                    'policies': pol})
                require(snapshot(data) == digest, 'v3n source fixture mutated')
            source_modes.append({'mode': mode, 'capacities': caps})
        rows.append({'schedule': label, 'source_external_ticks': list(ticks),
                     'modes': source_modes})
    native_cells = len(NEW_SCHEDULES)*len(ARMS)*len(CAPACITIES)
    derived_cells = native_cells*len(POLICIES)*len(QUOTAS)
    require(native_cells == 18 and derived_cells == 72 and
            comparisons['strict_native_parity_cells'] == derived_cells and
            comparisons['policy_pairs'] == comparisons['ACK_first_inline_not_less'] == 36 and
            comparisons['quota_pairs'] == 36 and
            nulls['runs'] == nulls['strict_native_parity'] == 36 and
            nulls['ACKs'] == nulls['consumer_receipts'] ==
                nulls['absence_certificates'] == 0 and
            all(g['ready_miss_ticks'] ==
                g['native_veto_miss_ticks'] + g['consumer_first_miss_ticks'] +
                g['ACK_first_resource_unproven_miss_ticks']
                for c in totals.values() for p in c.values() for g in p.values()) and
            thresholds['16'] > 0 and len(long_gap_witnesses) > 0 and
            read_pinned_source(root) == source and
            read_pinned_sources(root) == arch and source_pins(root) == pins,
            'v3n-v3p missing admitted source gap or full parity evidence')
    return {
        'source_matrix': rows,
        'source_gap_totals': totals,
        'missed_ready_tick_threshold_contexts': thresholds,
        'long_ready_gap_source_witnesses': long_gap_witnesses,
        'nonmonotone_new_quota_witnesses': quota_inversions,
        'policy_quota_comparisons': comparisons,
        'causal_nulls': nulls,
        'new_original_native_runs': native_cells,
        'new_derived_gap_runs': derived_cells,
        'new_causal_null_runs': nulls['runs'],
        'exact_source_ready_gap_classification': True,
        'strict_full_native_projection': True,
        'all_frozen_source_pins_preserved': True,
    }


def build_report(prev, raw, result=None):
    validate_v3klm(prev, raw)
    require(result is None or (
            result['new_original_native_runs'] == 18 and
            result['new_derived_gap_runs'] == 72 and
            result['new_causal_null_runs'] == 36 and
            result['strict_full_native_projection'] and
            result['exact_source_ready_gap_classification'] and
            result['all_frozen_source_pins_preserved'] and
            result['missed_ready_tick_threshold_contexts']['16'] > 0),
            'v3n-v3p finite-source wait and native null evidence incomplete')
    return {
        'schema': SCHEMA,
        'status': STATUS if result else CONTRACT,
        'reference_v3klm_sha256': sha256(raw).hexdigest(),
        'stages': [
            'v3n-source-owned-ready-ACK-per-tick-exact-wait-classification',
            'v3o-new-admitted-eight-event-burst-PE-quota-policy-gap-matrix',
            'v3p-finite-deadline-counterexamples-and-future-opportunity-boundary',
        ],
        'admission_scope': {
            'topology': 'frozen-three-node-PE-spread-source-bridge',
            'max_external_events_per_fixture': 8,
            'last_admissible_external_tick': 32,
            'new_eight_event_schedules': [name for name, _ in NEW_SCHEDULES],
        },
        'new_original_native_runs': result['new_original_native_runs'] if result else 0,
        'new_derived_gap_runs': result['new_derived_gap_runs'] if result else 0,
        'new_causal_null_runs': result['new_causal_null_runs'] if result else 0,
        'source_gap_totals': result['source_gap_totals'] if result else None,
        'missed_ready_tick_threshold_contexts':
            result['missed_ready_tick_threshold_contexts'] if result else None,
        'long_ready_gap_source_witnesses':
            result['long_ready_gap_source_witnesses'] if result else None,
        'nonmonotone_new_quota_witnesses':
            result['nonmonotone_new_quota_witnesses'] if result else None,
        'policy_quota_comparisons': result['policy_quota_comparisons'] if result else None,
        'causal_nulls': result['causal_nulls'] if result else None,
        'source_matrix': result['source_matrix'] if result else None,
        'source_only_finite_deadline_threshold_refutation': bool(result),
        'no_future_source_opportunity_rate_or_per_actor_deadline_proven': True,
        'full_original_native_projection_preserved': bool(result),
        'native_actor_learning_observed': False,
        'native_operator_updates': 0,
        'claims_excluded': list(EXCLUSIONS),
        'next_gate': 'BLOCKED_NATIVE_MAX_GAP_ASSUMPTION_AND_ACTOR_SCHEDULER_CONTRACT',
    }
