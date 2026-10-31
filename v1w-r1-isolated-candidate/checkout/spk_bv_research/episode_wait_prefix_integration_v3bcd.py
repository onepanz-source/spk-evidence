"""v3b-v3d: native-backed source episode extension, ACK waits and prefixes.

A derived consumer-turn preference never overrides frozen-native readiness.
Observed ACK wait under a native veto is a direct finite counterexample to
claiming a global one-tick ACK deadline based solely on local queue fairness.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import (
    require, source_pins, runtime_modules_bound, snapshot,
)
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources
from spk_bv_research.actor_priority_contention_integration_v2m import _payload
from spk_bv_research.link_pressure_v0u import ARMS, _arm
from spk_bv_research.burst_window_cumulative_v2yza import (
    _run_derived, validate_v2vwx,
)
from spk_backvalidation_v2.derived_native_fork_v2g import read_pinned_source
from spk_backvalidation_v2.derived_actor_queue_fairness_v2v import POLICIES
from spk_backvalidation_v2.derived_ack_wait_audit_v3b import (
    audit_source_acks_and_paid_receipts, EpisodeWaitPlan, validate_episode_plan,
)

SCHEMA = 'spk-bv-source-episode-prefix-and-native-veto-wait-discriminator/v3b-v3d'
STATUS = 'DERIVED_SOURCE_EPISODE_PREFIX_ACK_WAIT_NATIVE_VETO_COUNTEREXAMPLE'
CONTRACT = 'V3B_V3D_SIGNED_V2YZA_PREDECESSOR_ONLY'
PREDECESSOR_SHA = '56d9208e1f0fd2f8dbad6c77030582f7dff8d7fdd1052ce7c2bc8a8c1fcb80f8'
SCHEDULES = (
    ('two', (1, 3)),
    ('three', (1, 3, 5)),
    ('four', (1, 3, 5, 7)),
    ('six', (1, 3, 5, 7, 9, 11)),
    ('eight_spaced', (1, 3, 5, 7, 9, 11, 13, 15)),
    ('eight_dense', (1, 2, 3, 4, 5, 6, 7, 8)),
)
PREFIX_SEQUENCE = ('two', 'three', 'four', 'six', 'eight_spaced')
GUARDS = (('strict_native_ready', True, True),
          ('actor_first_null_guard', False, False))
INTERVENTIONS = ('credit_zero', 'transport_loss')
EXCLUSIONS = (
    'source_events_are_admitted_external_episodes_not_forged_receiver_controls',
    'prefix_equivalence_is_only_for_pinned_source_times_before_new_input',
    'two_PE_source_capacity_is_not_frozen_native_actor_policy_adoption',
    'local_consumer_turn_bound_does_not_bound_native_veto_duration',
    'observed_native_veto_ACK_wait_refutes_unqualified_one_tick_deadline',
    'no_universal_queue_starvation_freedom_completion_or_termination_proof',
    'no_native_actor_learning_cross_node_authenticity_or_hardware_calibration',
    'loss_zero_credit_and_silence_are_not_negative_judgments',
)


def validate_v2yza(prev, raw):
    require(type(prev) is dict and type(raw) is bytes and canon(prev) == raw and
            sha256(raw).hexdigest() == PREDECESSOR_SHA,
            'v3b-v3d signed v2yza report canonical/SHA drift')
    require(prev.get('schema') ==
            'spk-bv-source-causal-multiturn-window-closure/v2y-v3a' and
            prev.get('status') ==
            'DERIVED_ACTIVATED_ACK_WINDOW_SOURCE_BURST_CONDITIONAL_NO_NATIVE_LIVENESS' and
            prev.get('reference_v2vwx_sha256') ==
            'c7cb06097b6d09f30a11a810cfd5b7e3197a773a2a0a7e29766f55bd41a553ef'
            and prev.get('new_native_runs') == 45 and
            prev.get('new_derived_policy_runs') == 270 and
            prev.get('new_derived_ablation_runs') == 225 and
            prev.get('bounded_window_activated_cells') == 7 and
            prev.get('bounded_window_activated_ticks') == 9 and
            prev.get('unbounded_two_turn_streak_cells') == 7 and
            prev.get('bounded_overrun_cells') == 0 and
            prev.get('ACK_journal_bound_intervention_cells') == 7 and
            prev.get('derived_finite_bounded_window_source_witness') is True and
            prev.get('universal_ACK_or_consumer_liveness_proven') is False and
            prev.get('native_queue_arbitration_or_learning_proven') is False and
            prev.get('native_operator_updates') == 0 and
            prev.get('next_gate') ==
                'BLOCKED_UNIVERSAL_PROGRESS_NATIVE_ACTOR_POLICY_AND_LEARNING',
            'v3b-v3d predecessor protocol/outcome/negative contract drift')
    rows = prev.get('native_matrix')
    require(type(rows) is list and len(rows) == 15 and
            len({r.get('label') for r in rows}) == 15,
            'v3b-v3d source predecessor missing independent organic workloads')
    for row in rows:
        require([mode.get('mode') for mode in row.get('modes', ())] ==
                [name for name, _, _ in ARMS],
                'v3b-v3d original native source controls incomplete')
        for mode in row['modes']:
            require(len(mode.get('source_native_sha256', '')) == 64 and
                    all(mode.get('guards', {}).get('strict_native_ready', {}).get(
                        policy, {}).get('native_equal') is True for policy in POLICIES),
                    'v3b-v3d predecessor full native parity missing')
    return True


def _prefix_until(rows, field, tick):
    require(type(rows) is list and type(tick) is int and tick >= 1 and
            all(type(r) is dict and type(r.get(field)) is int for r in rows),
            'v3c non-causal prefix timeline')
    return [r for r in rows if r[field] < tick]


def experiment(prev, raw, *, root: Path, fixture_fn, native_executor, plan_type):
    validate_v2yza(prev, raw)
    validate_episode_plan(EpisodeWaitPlan())
    root = root.resolve(strict=True)
    pins = source_pins(root)
    arch = read_pinned_sources(root)
    runtime_modules_bound(root, native_executor, fixture_fn, plan_type)
    source = read_pinned_source(root)
    model = {guard: {p: {
        'cells': 0, 'full_native_equal': 0, 'functional_payload_equal': 0,
        'ACK_count': 0, 'paid_consumer_count': 0,
        'ACK_wait_max_ticks': 0, 'ACK_wait_total_ticks': 0,
        'ACK_wait_positive_count': 0, 'consumer_paid_wait_max_ticks': 0,
        'bounded_ACK_preference_ticks': 0,
        'bounded_actual_ACK_grants': 0,
        'max_competing_consumer_streak': 0,
    } for p in POLICIES} for guard, _, _ in GUARDS}
    causals = {k: {'cells': 0, 'native_restored': 0,
                   'ACK_count': 0, 'consumer_receipts': 0}
               for k in INTERVENTIONS}
    rows = []
    captured_series = {}
    source_event_count = 0
    for schedule, ticks in SCHEDULES:
        case, fabric, plans = fixture_fn(ticks=ticks)
        require(tuple(e.timestamp for e in case.events) == ticks and
                all(e.node_id == 'A' and e.channel == 0 for e in case.events) and
                len(case.events) <= EpisodeWaitPlan().max_source_external_events,
                'v3b forged or unadmitted native source episodes')
        adjusted = (plans[0], replace(plans[1], fabric_slots_per_tick=2),
                    plans[2], plans[3])
        data = (case, fabric, adjusted)
        digest = snapshot(data)
        source_event_count += len(ticks)*len(ARMS)
        modes = []
        for mode, enabled, priority in ARMS:
            captured = {}

            def capture(*args, **kwargs):
                captured['native'] = native_executor(*args, **kwargs)
                return captured['native']

            native_signed = _arm(capture, plan_type, case, fabric, adjusted,
                'v3b-native-'+schedule+'-'+mode, enabled, priority, digest, data)
            native = captured['native']
            guards = {}
            for guard, forward, bv in GUARDS:
                policies = {}
                for policy in POLICIES:
                    summary, ACKs, paid, probes, witness, projected = _run_derived(
                        source, native_executor, plan_type, case, fabric,
                        adjusted, enabled, priority, digest, data,
                        label='v3b-'+schedule+'-'+policy,
                        policy=policy, forward=forward, bv=bv)
                    wait = audit_source_acks_and_paid_receipts(
                        ACKs, paid, witness, policy)
                    exact = projected == native
                    functional = (_payload(projected['forward']) ==
                                  _payload(native['forward']))
                    require(functional and (guard != 'strict_native_ready' or exact),
                            'v3b extended native source projected or functional drift')
                    x = model[guard][policy]
                    x['cells'] += 1
                    x['full_native_equal'] += int(exact)
                    x['functional_payload_equal'] += int(functional)
                    x['ACK_count'] += wait['source_ACKs']
                    x['paid_consumer_count'] += wait[
                        'independently_paid_consumer_receipts']
                    x['ACK_wait_max_ticks'] = max(x['ACK_wait_max_ticks'],
                        wait['max_ACK_due_to_service_wait_ticks'])
                    x['ACK_wait_total_ticks'] += wait[
                        'total_ACK_due_to_service_wait_ticks']
                    x['ACK_wait_positive_count'] += wait['ACK_wait_positive_count']
                    x['consumer_paid_wait_max_ticks'] = max(
                        x['consumer_paid_wait_max_ticks'],
                        wait['max_ACK_service_to_consumer_wait_ticks'])
                    x['bounded_ACK_preference_ticks'] += wait[
                        'bounded_turn_source_windows']
                    x['bounded_actual_ACK_grants'] += wait[
                        'actual_ACK_grants_on_bounded_windows']
                    x['max_competing_consumer_streak'] = max(
                        x['max_competing_consumer_streak'],
                        wait['max_competing_consumer_streak'])
                    policies[policy] = {
                        'full_original_native_equal': exact,
                        'functional_payload_equal': functional,
                        'source_ACKs': len(ACKs), 'paid_consumer_receipts': len(paid),
                        'max_ACK_wait_ticks': wait['max_ACK_due_to_service_wait_ticks'],
                        'total_ACK_wait_ticks': wait['total_ACK_due_to_service_wait_ticks'],
                        'bounded_ACK_preference_ticks': wait['bounded_turn_source_windows'],
                        'ACK_journal_sha256': sha256(canon(ACKs)).hexdigest(),
                        'paid_journal_sha256': sha256(canon(paid)).hexdigest(),
                    }
                    captured_series[(schedule, mode, guard, policy)] = (
                        ACKs, paid, projected['forward']['terminal'])
                guards[guard] = policies
            # Two independent causal-null probes per source schedule/mode.
            for intervention in INTERVENTIONS:
                summary, ACKs, paid, _, _, projected = _run_derived(
                    source, native_executor, plan_type, case, fabric,
                    adjusted, enabled, priority, digest, data,
                    label='v3d-'+schedule+'-'+intervention,
                    policy='bounded-turns', forward=False, bv=False,
                    intervention=intervention)
                require(projected == native and not ACKs and not paid,
                        'v3d causal null generated source ACK, paid charge or native drift')
                z = causals[intervention]
                z['cells'] += 1
                z['native_restored'] += 1
                z['ACK_count'] += len(ACKs)
                z['consumer_receipts'] += len(paid)
            modes.append({'mode': mode,
                          'original_native_sha256': native_signed['whole_result_sha256'],
                          'policies': guards})
        rows.append({'source_schedule': schedule,
                     'native_external_event_ticks': list(ticks), 'modes': modes})
        require(snapshot((case, fabric, adjusted)) == digest,
                'v3b original source fixture mutated during episode replay')
    # Source-causal no-anticipation: adding events in the future may not rewrite
    # the already executed ACK, independently paid consumer or forward prefix.
    prefix = {'comparisons': 0, 'ACK_prefix_equal': 0,
              'consumer_prefix_equal': 0, 'terminal_prefix_equal': 0}
    known = dict(SCHEDULES)
    for older, newer in zip(PREFIX_SEQUENCE, PREFIX_SEQUENCE[1:]):
        cut = known[newer][len(known[older])]
        require(known[newer][:len(known[older])] == known[older],
                'v3c source input suffix is not an admitted future extension')
        for mode, _, _ in ARMS:
            for guard, _, _ in GUARDS:
                for policy in POLICIES:
                    before = captured_series[(older, mode, guard, policy)]
                    after = captured_series[(newer, mode, guard, policy)]
                    ACK_equal = (_prefix_until(before[0], 'serviced_tick', cut) ==
                                 _prefix_until(after[0], 'serviced_tick', cut))
                    paid_equal = (_prefix_until(before[1], 'consume_tick', cut) ==
                                  _prefix_until(after[1], 'consume_tick', cut))
                    terminal_equal = (_prefix_until(before[2], 'timestamp', cut) ==
                                      _prefix_until(after[2], 'timestamp', cut))
                    require(ACK_equal and paid_equal and terminal_equal,
                            'v3c causal prefix unexpectedly rewritten by later source events')
                    prefix['comparisons'] += 1
                    prefix['ACK_prefix_equal'] += int(ACK_equal)
                    prefix['consumer_prefix_equal'] += int(paid_equal)
                    prefix['terminal_prefix_equal'] += int(terminal_equal)
    a = model['actor_first_null_guard']
    strict = model['strict_native_ready']
    require(all(m['cells'] == 18 and m['functional_payload_equal'] == 18
                for guard in model.values() for m in guard.values()) and
            all(m['full_native_equal'] == 18 for m in strict.values()) and
            all(x['cells'] == x['native_restored'] == 18 for x in causals.values()) and
            prefix['comparisons'] == prefix['ACK_prefix_equal'] ==
                prefix['consumer_prefix_equal'] == prefix['terminal_prefix_equal'] == 72 and
            a['consumer-first']['ACK_wait_max_ticks'] >
                a['bounded-turns']['ACK_wait_max_ticks'] and
            a['consumer-first']['ACK_wait_total_ticks'] >
                a['bounded-turns']['ACK_wait_total_ticks'] and
            a['bounded-turns']['ACK_wait_max_ticks'] == 1 and
            a['bounded-turns']['bounded_ACK_preference_ticks'] > 0 and
            strict['bounded-turns']['ACK_wait_max_ticks'] >
                a['bounded-turns']['ACK_wait_max_ticks'] and
            strict['bounded-turns']['ACK_wait_max_ticks'] ==
                strict['consumer-first']['ACK_wait_max_ticks'] and
            source_pins(root) == pins and
            read_pinned_sources(root) == arch and
            read_pinned_source(root) == source,
            'v3b-v3d finite source latency/prefix/native counterexample closure failed')
    return {
        'source_episode_matrix': rows,
        'ACK_wait_and_queue_priority_totals': model,
        'null_intervention_totals': causals,
        'prefix_causal_nonanticipation': prefix,
        'new_original_native_runs': len(SCHEDULES)*len(ARMS),
        'new_derived_queue_runs': len(SCHEDULES)*len(ARMS)*len(GUARDS)*len(POLICIES),
        'new_derived_null_runs': len(SCHEDULES)*len(ARMS)*len(INTERVENTIONS),
        'source_admitted_external_events_across_native_contexts': source_event_count,
        'null_guard_bounded_max_ACK_wait_ticks':
            a['bounded-turns']['ACK_wait_max_ticks'],
        'null_guard_unbounded_max_ACK_wait_ticks':
            a['consumer-first']['ACK_wait_max_ticks'],
        'strict_native_veto_max_ACK_wait_ticks':
            strict['bounded-turns']['ACK_wait_max_ticks'],
        'local_turn_bound_does_not_imply_global_one_tick_deadline': True,
        'source_frozen': True,
    }


def build_report(prev, raw, result=None):
    validate_v2yza(prev, raw)
    require(result is None or (
            result['source_frozen'] and
            result['new_original_native_runs'] == 18 and
            result['new_derived_queue_runs'] == 108 and
            result['new_derived_null_runs'] == 36 and
            result['prefix_causal_nonanticipation']['comparisons'] == 72 and
            result['strict_native_veto_max_ACK_wait_ticks'] >
                result['null_guard_bounded_max_ACK_wait_ticks']),
            'v3b-v3d contract lacks measured native veto / prefixes')
    return {
        'schema': SCHEMA,
        'status': STATUS if result else CONTRACT,
        'reference_v2yza_sha256': sha256(raw).hexdigest(),
        'cumulative_research_stages': [
            'v3b-2-to-8-admitted-external-source-episode-wait-horizon',
            'v3c-72-causal-prefix-no-anticipation-checks',
            'v3d-native-veto-global-ACK-deadline-counterexample-and-null-audit',
        ],
        'new_original_native_runs': result['new_original_native_runs'] if result else 0,
        'new_derived_queue_runs': result['new_derived_queue_runs'] if result else 0,
        'new_derived_null_runs': result['new_derived_null_runs'] if result else 0,
        'source_admitted_external_events_across_native_contexts': (
            result['source_admitted_external_events_across_native_contexts'] if result else 0),
        'null_guard_bounded_max_ACK_wait_ticks': (
            result['null_guard_bounded_max_ACK_wait_ticks'] if result else None),
        'null_guard_unbounded_max_ACK_wait_ticks': (
            result['null_guard_unbounded_max_ACK_wait_ticks'] if result else None),
        'strict_native_veto_max_ACK_wait_ticks': (
            result['strict_native_veto_max_ACK_wait_ticks'] if result else None),
        'prefix_causal_nonanticipation': (
            result['prefix_causal_nonanticipation'] if result else None),
        'ACK_wait_and_queue_priority_totals': (
            result['ACK_wait_and_queue_priority_totals'] if result else None),
        'null_intervention_totals': (
            result['null_intervention_totals'] if result else None),
        'source_episode_matrix': result['source_episode_matrix'] if result else None,
        'derived_finite_conditional_queue_wait_witness': bool(result),
        'native_veto_global_deadline_counterexample_observed': bool(result),
        'universal_ACK_or_consumer_liveness_proven': False,
        'frozen_native_actor_learning_or_priority_contract_proven': False,
        'native_operator_updates': 0,
        'next_gate': 'BLOCKED_NATIVE_GLOBAL_PROGRESS_BEYOND_SOURCE_WINDOW_AND_LEARNING',
        'claims_excluded': list(EXCLUSIONS),
    }
