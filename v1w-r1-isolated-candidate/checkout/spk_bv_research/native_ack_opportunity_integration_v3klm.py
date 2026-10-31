"""v3k-v3m: conditional source-native ACK opportunity, policy and PE test.

Only the frozen source's derived actor fork is used; the original source actor
contract is never rebound. No bound on the arrival of a future opportunity is
inferred from these finite experiments.
"""
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
from spk_backvalidation_v2.derived_native_opportunity_certificate_v3k import (
    POLICIES, audit_native_opportunities,
)

SCHEMA = 'spk-bv-finite-conditional-native-ACK-opportunity-discriminator/v3k-v3m'
STATUS = 'DERIVED_NATIVE_ACK_OPPORTUNITY_RESOURCE_AND_QUEUE_CONDITIONAL_NO_LIVENESS'
CONTRACT = 'V3K_V3M_SIGNED_V3HIJ_PREDECESSOR_ONLY'
PREDECESSOR_SHA = '0d441433aaa99abb06beab7dffc65ce8c7a886fdfd98c21086bc41ea992aa2c4'
CAPACITIES = (1, 2)
QUOTAS = (1, 2)
NULLS = ('zero_credit', 'transport_loss')
EXCLUSIONS = (
    'native_veto_free_and_ready_is_not_sufficient_when_consumer_first',
    'ACK_first_feasible_grant_is_a_local_conditional_derived_source_fact',
    'finite_opportunity_counts_do_not_bound_when_future_native_slack_arrives',
    'native_PE_capacity_changes_are_reference_experiments_not_policy_changes',
    'tail_off_unconsumed_is_not_negative_judgment_or_silence_proof',
    'actor_credit_ACK_is_not_unpaid_learning_or_frozen_native_actor_update',
    'no_global_native_liveness_starvation_freedom_or_hardware_claim',
)


def validate_v3hij(prev, raw):
    require(type(prev) is dict and type(raw) is bytes and canon(prev) == raw and
            sha256(raw).hexdigest() == PREDECESSOR_SHA and
            prev.get('schema') ==
            'spk-bv-native-safe-derived-ACK-tail-opportunity-boundary/v3h-v3j' and
            prev.get('status') ==
            'DERIVED_FINITE_ACK_TAIL_CUTOVER_PREFIX_RESOURCE_ENVELOPE_NO_NATIVE_LIVENESS' and
            prev.get('reference_v3efg_sha256') ==
            '93fd26296492945629f0d93dfc6fbb2e41f69b6ae8d009813b447db1c1ffc4f3' and
            prev.get('new_native_runs') == 27 and
            prev.get('new_derived_budget_runs') == 454 and
            prev.get('new_causal_null_runs') == 54 and
            prev.get('exact_finite_cutovers') == 54 and
            prev.get('total_source_tail_prefix_comparisons') == 454 and
            prev.get('total_source_capacity_monotonicity_comparisons') == 400 and
            prev.get('full_strict_native_result_projection_preserved') is True and
            prev.get('universal_ACK_deadline_or_native_learning_proven') is False and
            prev.get('native_operator_updates') == 0 and
            prev.get('next_gate') ==
            'BLOCKED_NATIVE_GUARANTEED_SERVICE_OPPORTUNITY_AND_ACTOR_LEARNING',
            'v3k-v3m noncanonical/tampered signed v3hij predecessor')
    matrix = prev.get('source_matrix')
    require(type(matrix) is list and len(matrix) == len(ALL_SCHEDULES) and
            [x.get('schedule') for x in matrix] ==
            [label for label, _ in ALL_SCHEDULES] and
            all([m.get('mode') for m in r['modes']] ==
                [name for name, _, _ in ARMS] for r in matrix) and
            all(q.get('exact_cutover_at_H_and_not_H_minus_one') is True
                for r in matrix for m in r['modes']
                for q in m['quotas'].values()),
            'v3k-v3m source predecessor capacity matrix incomplete')
    return True


def _run_source(source, native_executor, plan_type, case, fabric, plans,
                enabled, priority, digest, data, *, quota, policy,
                intervention='normal'):
    require(type(quota) is int and quota in QUOTAS and policy in POLICIES and
            intervention in ('normal', *NULLS),
            'v3k invalid queue/PE/native/null experiment')
    port = ReceiverPortV2h(
        latency=2, accept=(lambda _: False)
        if intervention == 'transport_loss' else None)
    actor = DerivedActorQueueFairnessV2v(
        port, queue_plan=ActorQueuePlanV2v(policy),
        admission_plan=CausalAdmissionPlanV2o(True, True),
        service_plan=ShadowServicePlanV2j(max_per_tick=quota, max_tail_ticks=0),
        credit_plan=(ActorCreditPlanV2l(max_abs_credit=0)
                     if intervention == 'zero_credit' else ActorCreditPlanV2l()))
    observer = CallsiteObserver()
    executor, _, semantics, anchors = derive_queue_fairness_executor(
        source, native_executor, port, actor, observer)
    captured = {}

    def run(*args, **kwargs):
        captured['derived'] = executor(*args, **kwargs)
        captured['projection'] = actor.project_original_native_result(
            captured['derived'])
        return captured['projection']

    _arm(run, plan_type, case, fabric, plans,
         'v3k-ACK-opportunity-'+policy+'-'+str(quota)+'-'+intervention,
         enabled, priority, digest, data)
    summary, receiver = actor.summary(), port.summary()
    ACKs, paid = actor.credit_journal(), actor.concurrent_journal()
    probes = actor.queue_fairness_probes()
    ledger = [dict(r) for r in actor._timeline]
    require(semantics == (('batch', 194), ('clock', 125), ('emission', 217),
                         ('ingress', 136)) and anchors == (158, 296, 307) and
            not observer.overflow and not observer.sink_failed and
            observer.counts()['_admit'] == 1 and
            summary['within_original_native_plan_capacity'] and
            summary['frozen_actor_state_changed'] is False and
            summary['native_operator_updates'] == 0 and
            summary['derived_control_tail_grants'] == 0 and
            summary['absence_certificates'] == 0 and
            summary['concurrent_consumer_PE_units'] == len(paid) and
            summary['concurrent_consumer_memory_units'] == 2*len(paid) and
            all(a['resource_phase'] == 'native-slack' for a in ACKs) and
            len(ledger) == len(probes),
            'v3k derived source/memory/control/queue custody drift')
    return ACKs, paid, probes, ledger, summary, receiver, captured['projection']


def _new_totals():
    return {'contexts': 0, 'strict_native_projection_cells': 0,
            'source_native_ticks': 0, 'source_inline_ACKs': 0,
            'source_pending_not_negative': 0,
            'real_paid_consumer_receipts': 0,
            'ready_native_veto_ticks': 0,
            'ready_nonveto_consumer_first_ticks': 0,
            'ready_nonveto_ACK_first_ticks': 0,
            'weak_no_veto_ready_without_ACK_ticks': 0,
            'sufficient_feasible_ACK_first_ticks': 0,
            'sufficient_feasible_ACK_first_progress_ticks': 0,
            'ACK_first_resource_unproven_ticks': 0,
            'ready_without_grant_streak_max': 0}


def experiment(prev, raw, *, root: Path, fixture_fn, native_executor, plan_type):
    validate_v3hij(prev, raw)
    root = root.resolve(strict=True)
    pins = source_pins(root)
    arch = read_pinned_sources(root)
    source = read_pinned_source(root)
    runtime_modules_bound(root, native_executor, fixture_fn, plan_type)
    totals = {str(cap): {policy: {str(q): _new_totals() for q in QUOTAS}
                         for policy in POLICIES} for cap in CAPACITIES}
    contrasts = {'policy_pairs': 0, 'ACK_first_at_least_bounded_inline': 0,
                 'ACK_first_more_inline': 0,
                 'quota_pairs': 0, 'higher_quota_not_less_inline': 0,
                 'higher_quota_fewer_inline': 0,
                 'higher_quota_strictly_more_inline': 0,
                 'normal_native_projection_exact': 0}
    quota_inversions = []
    nulls = {name: {'runs': 0, 'native_exact': 0, 'ACKs': 0,
                    'paid': 0, 'absence_certificates': 0}
             for name in NULLS}
    rows = []
    for label, ticks in ALL_SCHEDULES:
        case, fabric, plans = fixture_fn(ticks=ticks)
        require(tuple(e.timestamp for e in case.events) == ticks and
                len(ticks) <= 8 and
                all(e.node_id == 'A' and e.channel == 0 for e in case.events),
                'v3k source unadmitted native event series')
        source_modes = []
        for mode, enabled, priority in ARMS:
            capacity_rows = []
            for cap in CAPACITIES:
                altered = (plans[0], replace(plans[1], fabric_slots_per_tick=cap),
                           plans[2], plans[3])
                data = (case, fabric, altered)
                digest = snapshot(data)
                captured = {}

                def capture(*args, **kwargs):
                    captured['native'] = native_executor(*args, **kwargs)
                    return captured['native']

                native_run = _arm(capture, plan_type, case, fabric, altered,
                    'v3k-original-native-'+label+'-'+mode+'-'+str(cap),
                    enabled, priority, digest, data)
                native = captured['native']
                stats = {}
                for policy in POLICIES:
                    by_quota = {}
                    for quota in QUOTAS:
                        ACKs, paid, probes, ledger, summary, receiver, projected = (
                            _run_source(source, native_executor, plan_type,
                                case, fabric, altered, enabled, priority,
                                digest, data, quota=quota, policy=policy))
                        audit = audit_native_opportunities(
                            ACKs, paid, probes, ledger, summary, receiver,
                            policy=policy, global_quota=quota,
                            native_PE_budget=cap)
                        require(projected == native and
                                audit['sufficient_feasible_ACK_first_ticks'] ==
                                audit['sufficient_feasible_ACK_first_progress_ticks'],
                                'v3k conditional ACK opportunity or strict source parity fails')
                        group = totals[str(cap)][policy][str(quota)]
                        group['contexts'] += 1
                        group['strict_native_projection_cells'] += 1
                        for key in _new_totals():
                            if key.endswith('_max'):
                                group[key] = max(group[key], audit[key])
                            elif key not in ('contexts',
                                             'strict_native_projection_cells'):
                                group[key] += audit[key]
                        contrasts['normal_native_projection_exact'] += 1
                        by_quota[str(quota)] = {
                            'native_exact': True,
                            'source_acks': len(ACKs),
                            'paid_consumer_receipts': len(paid),
                            'source_control_delivered': receiver['control_delivered'],
                            'ACK_journal_sha256': sha256(canon(ACKs)).hexdigest(),
                            'audit': audit,
                        }
                    stats[policy] = by_quota
                for q in QUOTAS:
                    contrasts['policy_pairs'] += 1
                    first = stats['ACK-first'][str(q)]['source_acks']
                    bounded = stats['bounded-turns'][str(q)]['source_acks']
                    contrasts['ACK_first_at_least_bounded_inline'] += int(
                        first >= bounded)
                    contrasts['ACK_first_more_inline'] += int(first > bounded)
                for policy in POLICIES:
                    contrasts['quota_pairs'] += 1
                    low, high = (stats[policy][str(q)]['source_acks']
                                 for q in QUOTAS)
                    contrasts['higher_quota_not_less_inline'] += int(high >= low)
                    contrasts['higher_quota_fewer_inline'] += int(high < low)
                    contrasts['higher_quota_strictly_more_inline'] += int(high > low)
                    if high < low:
                        quota_inversions.append({
                            'schedule': label, 'mode': mode,
                            'native_PE_capacity': cap,
                            'queue_policy': policy,
                            'quota_one_inline_ACKs': low,
                            'quota_two_inline_ACKs': high,
                            'quota_one_ACK_journal_sha256':
                                stats[policy]['1']['ACK_journal_sha256'],
                            'quota_two_ACK_journal_sha256':
                                stats[policy]['2']['ACK_journal_sha256'],
                        })
                for intervention in NULLS:
                    a, paid, _, _, summary, receiver, projected = _run_source(
                        source, native_executor, plan_type, case, fabric,
                        altered, enabled, priority, digest, data, quota=2,
                        policy='ACK-first', intervention=intervention)
                    require(projected == native and not a and not paid and
                            receiver['absence_certificates'] == 0 and
                            summary['derived_control_tail_grants'] == 0,
                            'v3m source null falsely served an ACK/created a negative')
                    n = nulls[intervention]
                    n['runs'] += 1
                    n['native_exact'] += 1
                capacity_rows.append({'native_PE_capacity': cap,
                    'source_native_sha256': native_run['whole_result_sha256'],
                    'policies': stats})
                require(snapshot((case, fabric, altered)) == digest,
                        'v3k source native fixture mutated during derived replay')
            source_modes.append({'mode': mode, 'capacities': capacity_rows})
        rows.append({'schedule': label, 'source_external_ticks': list(ticks),
                     'modes': source_modes})
    contexts = len(ALL_SCHEDULES)*len(ARMS)*len(CAPACITIES)
    per_capacity_contexts = len(ALL_SCHEDULES)*len(ARMS)
    expected_derived = contexts*len(POLICIES)*len(QUOTAS)
    require(contrasts['normal_native_projection_exact'] == expected_derived and
            contrasts['policy_pairs'] == contexts*len(QUOTAS) and
            contrasts['quota_pairs'] == contexts*len(POLICIES) and
            all(x['contexts'] == x['strict_native_projection_cells'] ==
                per_capacity_contexts
                for c in totals.values() for p in c.values()
                for x in p.values()) and
            all(x['sufficient_feasible_ACK_first_ticks'] ==
                x['sufficient_feasible_ACK_first_progress_ticks']
                for c in totals.values() for p in c.values()
                for x in p.values()) and
            all(n['runs'] == n['native_exact'] == contexts and
                n['ACKs'] == n['paid'] == n['absence_certificates'] == 0
                for n in nulls.values()) and
            sum(x['weak_no_veto_ready_without_ACK_ticks']
                for c in totals.values() for x in c['bounded-turns'].values()) > 0 and
            contrasts['ACK_first_more_inline'] > 0 and
            contrasts['higher_quota_strictly_more_inline'] > 0 and
            contrasts['higher_quota_fewer_inline'] == len(quota_inversions) and
            read_pinned_source(root) == source and
            source_pins(root) == pins and read_pinned_sources(root) == arch,
            'v3k-v3m source opportunity/actor queue/causal null closure failed')
    return {
        'source_matrix': rows,
        'per_native_capacity_policy_quota_totals': totals,
        'policy_and_global_resource_contrasts': contrasts,
        'nonmonotone_inline_quota_witnesses': quota_inversions,
        'causal_null_totals': nulls,
        'new_original_native_runs': contexts,
        'new_derived_policy_runs': expected_derived,
        'new_causal_null_runs': contexts*len(NULLS),
        'sufficient_source_opportunities': sum(
            x['sufficient_feasible_ACK_first_ticks']
            for c in totals.values() for p in c.values() for x in p.values()),
        'unsafe_weak_no_veto_opportunities': sum(
            x['weak_no_veto_ready_without_ACK_ticks']
            for c in totals.values() for p in c.values() for x in p.values()),
        'frozen_source_pins_preserved': True,
    }


def build_report(prev, raw, result=None):
    validate_v3hij(prev, raw)
    require(result is None or (
        result['frozen_source_pins_preserved'] and
        result['new_original_native_runs'] == 54 and
        result['new_derived_policy_runs'] == 216 and
        result['new_causal_null_runs'] == 108 and
        result['sufficient_source_opportunities'] > 0 and
        result['unsafe_weak_no_veto_opportunities'] > 0),
        'v3k-v3m missing native-safe conditional actor ACK opportunity evidence')
    return {
        'schema': SCHEMA,
        'status': STATUS if result else CONTRACT,
        'reference_v3hij_sha256': sha256(raw).hexdigest(),
        'cumulative_research_stages': [
            'v3k-source-backed-native-veto-free-and-resource-eligible-ACK-opportunity',
            'v3l-ACK-first-versus-bounded-consumer-queue-priority-factorial',
            'v3m-one-vs-two-PE-and-global-ACK-quota-conditional-progress-and-causal-nulls',
        ],
        'new_original_native_runs': result['new_original_native_runs'] if result else 0,
        'new_derived_policy_runs': result['new_derived_policy_runs'] if result else 0,
        'new_causal_null_runs': result['new_causal_null_runs'] if result else 0,
        'sufficient_source_opportunities':
            result['sufficient_source_opportunities'] if result else 0,
        'unsafe_weak_no_veto_opportunities':
            result['unsafe_weak_no_veto_opportunities'] if result else 0,
        'per_native_capacity_policy_quota_totals':
            result['per_native_capacity_policy_quota_totals'] if result else None,
        'policy_and_global_resource_contrasts':
            result['policy_and_global_resource_contrasts'] if result else None,
        'nonmonotone_inline_quota_witnesses':
            result['nonmonotone_inline_quota_witnesses'] if result else None,
        'causal_null_totals': result['causal_null_totals'] if result else None,
        'source_matrix': result['source_matrix'] if result else None,
        'source_conditional_ACK_opportunity_observed': bool(result),
        'strict_full_original_native_projection_preserved': bool(result),
        'universal_ACK_liveness_or_native_learning_proven': False,
        'native_operator_updates': 0,
        'next_gate': 'BLOCKED_GLOBAL_NATIVE_OPPORTUNITY_RATE_OR_FAIR_SCHEDULER_CONTRACT',
        'claims_excluded': list(EXCLUSIONS),
    }
