"""BV v3q-v3s: source-owned per-actor ACK work versus global progress.

Only the already pinned derived execution receives control.  The original
native result is projected exactly and its implementation stays frozen.
"""
from __future__ import annotations

from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path

from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import (
    require, runtime_modules_bound, snapshot, source_pins,
)
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources
from spk_bv_research.link_pressure_v0u import ARMS, _arm
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
from spk_backvalidation_v2.derived_actor_service_gap_v3q import audit_actor_service_gap

SCHEMA = 'spk-bv-source-actor-specific-ACK-progress-counterexample/v3q-v3s'
STATUS = 'DERIVED_ACTOR_SPECIFIC_READY_ACK_CUSTODY_PEER_PROGRESS_NO_NATIVE_FAIRNESS'
CONTRACT = 'V3Q_V3S_SIGNED_V3NOP_PREDECESSOR_ONLY'
PREDECESSOR_SHA = 'bbfd059007f2b8c18c4833b207859c277ff04648fa076246085e215470000f94'
NEW_SCHEDULES = (
    ('eight_split_burst', (1, 2, 3, 4, 9, 10, 11, 12)),
    ('eight_three_stride', (3, 6, 9, 12, 15, 18, 21, 24)),
    ('eight_alternating_pairs', (2, 3, 7, 8, 12, 13, 17, 18)),
)
CAPACITIES = (1, 2)
QUOTAS = (1, 2)
POLICIES = ('ACK-first', 'bounded-turns')
NULLS = ('transport_loss', 'zero_credit')
EXCLUSIONS = (
    'one_global_ACK_grant_does_not_serve_every_waiting_actor',
    'source_actor_address_custody_is_not_cryptographic_identity',
    'per_actor_ready_wait_is_measured_on_finite_source_native_ticks_only',
    'post_native_deliveries_are_not_relabelled_as_native_ready_controls',
    'native_horizon_unserviced_actor_mailbox_is_censored_not_a_negative_judgment',
    'global_quota_and_ACK_first_are_derived_policies_not_native_learning',
    'no_individual_native_actor_deadline_or_universal_fair_scheduler_guarantee',
    'no_frozen_neuron_memory_or_operator_updates',
)


def validate_v3nop(prev, raw):
    require(type(prev) is dict and type(raw) is bytes and canon(prev) == raw and
            sha256(raw).hexdigest() == PREDECESSOR_SHA and
            prev.get('schema') ==
              'spk-bv-source-native-ready-ACK-gap-and-proof-boundary/v3n-v3p' and
            prev.get('status') ==
              'DERIVED_FINITE_READY_ACK_WAIT_GAP_SOURCE_DISCRIMINATOR_NO_GLOBAL_DEADLINE' and
            prev.get('reference_v3klm_sha256') ==
              '6fe69d43c3e4ef75e7162ef053903780ad7a470b9f8603220bee607dba761607' and
            prev.get('new_original_native_runs') == 18 and
            prev.get('new_derived_gap_runs') == 72 and
            prev.get('new_causal_null_runs') == 36 and
            prev.get('missed_ready_tick_threshold_contexts') ==
              {'1': 72, '2': 72, '4': 72, '8': 66, '16': 53, '32': 24} and
            prev.get('source_only_finite_deadline_threshold_refutation') is True and
            prev.get('no_future_source_opportunity_rate_or_per_actor_deadline_proven') is True and
            prev.get('full_original_native_projection_preserved') is True and
            prev.get('native_actor_learning_observed') is False and
            prev.get('native_operator_updates') == 0 and
            prev.get('next_gate') ==
              'BLOCKED_NATIVE_MAX_GAP_ASSUMPTION_AND_ACTOR_SCHEDULER_CONTRACT' and
            type(prev.get('source_matrix')) is list and
            len(prev['source_matrix']) == 3 and
            len(prev.get('nonmonotone_new_quota_witnesses', [])) == 3,
            'v3q-v3s signed v3nop source predecessor altered or incomplete')
    return True


def _run_actor(source, native_executor, plan_type, case, fabric, plans,
               enabled, priority, digest, data, *, quota, policy,
               intervention='normal'):
    require(type(quota) is int and quota in QUOTAS and policy in POLICIES and
            intervention in ('normal', *NULLS),
            'v3q invalid source actor ACK experiment')
    port = ReceiverPortV2h(latency=2,
        accept=(lambda _: False) if intervention == 'transport_loss' else None)
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
        captured['projected'] = actor.project_original_native_result(
            captured['derived'])
        return captured['projected']

    _arm(run, plan_type, case, fabric, plans,
         'v3q-actor-gap-'+policy+'-'+str(quota)+'-'+intervention,
         enabled, priority, digest, data)
    summary, receiver = actor.summary(), port.summary()
    ack, paid, probes = (actor.credit_journal(), actor.concurrent_journal(),
                         actor.queue_fairness_probes())
    ledger = [dict(row) for row in actor._timeline]
    records = [asdict(rec) for name in sorted(actor._actors)
               for rec in port.mailbox(name)]
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
            all(a['resource_phase'] == 'native-slack' for a in ack) and
            len(probes) == len(ledger) and
            len(records) == receiver['control_delivered'],
            'v3q native source actor-credit/consumer/mailbox resource drift')
    return ack, paid, probes, ledger, summary, receiver, records, captured['projected']


def experiment(prev, raw, *, root: Path, fixture_fn, native_executor, plan_type):
    validate_v3nop(prev, raw)
    root = root.resolve(strict=True)
    pins, arch, source = source_pins(root), read_pinned_sources(root), read_pinned_source(root)
    runtime_modules_bound(root, native_executor, fixture_fn, plan_type)
    prior_ticks = {tuple(r['source_external_ticks']) for r in prev['source_matrix']}
    totals = {'native_original_runs': 0, 'derived_actor_runs': 0,
              'causal_null_runs': 0, 'full_native_projection_cells': 0,
              'source_delivered': 0, 'native_inline_ACKs': 0,
              'native_ready_actor_ticks': 0, 'native_missed_actor_ticks': 0,
              'source_peer_progress_actor_misses': 0,
              'global_grant_with_unserved_actor_ticks': 0,
              'post_native_deliveries': 0, 'native_horizon_censored_records': 0,
              'maximum_actor_ready_miss_streak': 0,
              'maximum_ACK_due_to_service_wait_ticks': 0,
              'at_least_two_actors_delivered_contexts': 0,
              'contexts_with_global_progress_peer_miss': 0}
    cases, counterexamples = [], []
    nulls = {'runs': 0, 'no_acks': 0, 'no_negative_certificates': 0,
             'full_original_native_projection': 0}
    for label, ticks in NEW_SCHEDULES:
        case, fabric, plans = fixture_fn(ticks=ticks)
        require(tuple(e.timestamp for e in case.events) == ticks and
                len(ticks) == 8 and max(ticks) <= 32 and
                all(e.node_id == 'A' and e.channel == 0 for e in case.events) and
                ticks not in prior_ticks,
                'v3q source episode not admitted or repeated from predecessor')
        modes = []
        for mode, enabled, priority in ARMS:
            capacities = []
            for cap in CAPACITIES:
                altered = (plans[0], replace(plans[1], fabric_slots_per_tick=cap),
                           plans[2], plans[3])
                data = (case, fabric, altered)
                digest = snapshot(data)
                captured = {}

                def capture(*args, **kwargs):
                    captured['native'] = native_executor(*args, **kwargs)
                    return captured['native']

                native_receipt = _arm(capture, plan_type, case, fabric, altered,
                    'v3q-original-'+label+'-'+mode+'-'+str(cap),
                    enabled, priority, digest, data)
                native = captured['native']
                totals['native_original_runs'] += 1
                policies = {}
                for policy in POLICIES:
                    quotas = {}
                    for quota in QUOTAS:
                        (acks, paid, probes, ledger, summary, receiver,
                         records, projected) = _run_actor(
                            source, native_executor, plan_type, case, fabric,
                            altered, enabled, priority, digest, data,
                            quota=quota, policy=policy)
                        audit = audit_actor_service_gap(
                            acks, paid, probes, ledger, summary, receiver,
                            records, policy=policy, global_quota=quota,
                            native_PE_budget=cap)
                        require(projected == native and
                                not audit['native_universal_actor_liveness_proven'] and
                                not audit['native_learning_proven'],
                                'v3q derived actor-local progress changes native output')
                        totals['derived_actor_runs'] += 1
                        totals['full_native_projection_cells'] += 1
                        totals['source_delivered'] += audit['source_delivered']
                        totals['native_inline_ACKs'] += audit['source_ack_count']
                        totals['native_missed_actor_ticks'] += audit['actor_ready_misses']
                        totals['global_grant_with_unserved_actor_ticks'] += audit[
                            'global_grant_with_unserved_actor_ticks']
                        totals['post_native_deliveries'] += audit[
                            'source_post_native_delivery_count']
                        totals['native_ready_actor_ticks'] += sum(
                            r['native_ready_actor_ticks']
                            for r in audit['actor_totals'].values())
                        totals['source_peer_progress_actor_misses'] += sum(
                            r['peer_progress_actor_misses']
                            for r in audit['actor_totals'].values())
                        totals['native_horizon_censored_records'] += sum(
                            r['unserved_at_native_end_censored']
                            for r in audit['actor_totals'].values())
                        totals['maximum_actor_ready_miss_streak'] = max(
                            totals['maximum_actor_ready_miss_streak'],
                            *(r['max_consecutive_ready_actor_misses']
                              for r in audit['actor_totals'].values()))
                        totals['maximum_ACK_due_to_service_wait_ticks'] = max(
                            totals['maximum_ACK_due_to_service_wait_ticks'],
                            *(r['max_ack_due_to_service_ticks']
                              for r in audit['actor_totals'].values()))
                        totals['at_least_two_actors_delivered_contexts'] += int(
                            len(audit['actor_totals']) >= 2)
                        if audit['global_grant_with_unserved_actor_ticks']:
                            totals['contexts_with_global_progress_peer_miss'] += 1
                            witness = audit['first_global_progress_actor_miss_witness']
                            counterexamples.append({
                                'schedule': label, 'native_mode': mode,
                                'native_PE_capacity': cap, 'policy': policy,
                                'global_ACK_quota': quota,
                                'native_result_sha256': native_receipt[
                                    'whole_result_sha256'],
                                'source_ACK_journal_sha256': sha256(canon(acks)).hexdigest(),
                                'witness': witness,
                            })
                        quotas[str(quota)] = {
                            'source_ACK_journal_sha256': sha256(canon(acks)).hexdigest(),
                            'full_original_native_result_exact': True,
                            'audit': audit,
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
                            'v3s actor null created ACK/silence/negative certificate')
                    nulls['runs'] += 1
                    nulls['no_acks'] += 1
                    nulls['no_negative_certificates'] += 1
                    nulls['full_original_native_projection'] += 1
                    totals['causal_null_runs'] += 1
                capacities.append({'native_PE_capacity': cap,
                    'original_native_result_sha256': native_receipt['whole_result_sha256'],
                    'policies': policies})
                require(snapshot(data) == digest, 'v3q source native fixture mutated')
            modes.append({'mode': mode, 'capacities': capacities})
        cases.append({'schedule': label, 'source_external_ticks': list(ticks),
                      'modes': modes})
    require(totals['native_original_runs'] == 18 and
            totals['derived_actor_runs'] ==
                totals['full_native_projection_cells'] == 72 and
            nulls['runs'] == nulls['no_acks'] ==
                nulls['no_negative_certificates'] ==
                nulls['full_original_native_projection'] ==
                totals['causal_null_runs'] == 36 and
            totals['native_ready_actor_ticks'] ==
                totals['native_missed_actor_ticks']+totals['native_inline_ACKs'] and
            totals['source_peer_progress_actor_misses'] > 0 and
            totals['contexts_with_global_progress_peer_miss'] > 0 and
            totals['at_least_two_actors_delivered_contexts'] > 0 and
            read_pinned_source(root) == source and
            read_pinned_sources(root) == arch and source_pins(root) == pins,
            'v3q-v3s source-backed per-actor peer ACK gap closure incomplete')
    return {'source_matrix': cases, 'actor_progress_totals': totals,
            'global_progress_not_actor_progress_witnesses': counterexamples,
            'causal_nulls': nulls,
            'exact_native_projection': True,
            'source_mailbox_and_ACK_actor_custody': True,
            'frozen_source_pins_preserved': True}


def build_report(prev, raw, result=None):
    validate_v3nop(prev, raw)
    require(result is None or (
        result['actor_progress_totals']['derived_actor_runs'] == 72 and
        result['actor_progress_totals']['native_original_runs'] == 18 and
        result['causal_nulls']['runs'] == 36 and
        len(result['global_progress_not_actor_progress_witnesses']) > 0 and
        result['exact_native_projection'] and
        result['source_mailbox_and_ACK_actor_custody'] and
        result['frozen_source_pins_preserved']),
        'v3q-v3s actor-specific source proof incomplete')
    return {
        'schema': SCHEMA, 'status': STATUS if result else CONTRACT,
        'reference_v3nop_sha256': sha256(raw).hexdigest(),
        'cumulative_research_stages': [
            'v3q-per-actor-source-mailbox-due-and-ACK-identity-reconstruction',
            'v3r-global-progress-with-other-actor-not-serviced-counterexamples',
            'v3s-new-eight-event-policy-capacity-matrix-and-native-horizon-censoring',
        ],
        'source_matrix': result['source_matrix'] if result else None,
        'actor_progress_totals': result['actor_progress_totals'] if result else None,
        'global_progress_not_actor_progress_witnesses': result[
            'global_progress_not_actor_progress_witnesses'] if result else None,
        'causal_nulls': result['causal_nulls'] if result else None,
        'new_original_native_runs': result['actor_progress_totals'][
            'native_original_runs'] if result else 0,
        'new_derived_actor_runs': result['actor_progress_totals'][
            'derived_actor_runs'] if result else 0,
        'new_causal_null_runs': result['causal_nulls']['runs'] if result else 0,
        'source_per_actor_ACK_custody_verified': bool(result),
        'aggregate_ACK_progress_insufficient_for_actor_liveness': bool(result),
        'full_original_native_result_projection_preserved': bool(result),
        'native_individual_actor_deadline_proven': False,
        'native_learning_observed': False, 'native_operator_updates': 0,
        'claims_excluded': list(EXCLUSIONS),
        'next_gate': 'BLOCKED_NATIVE_PER_ACTOR_FAIR_SCHEDULING_AND_SERVICE_RATE_CONTRACT',
    }
