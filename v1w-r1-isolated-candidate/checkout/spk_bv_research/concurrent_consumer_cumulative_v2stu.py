"""Cumulative v2s-v2u research: concurrent paid service, causal deltas, audit.

All runs separately compile the pinned frozen native scheduler. No user/native
file or native operator is modified; a native priority contract remains open.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVRejected
from spk_backvalidation_v2.derived_native_fork_v2g import CallsiteObserver
from spk_backvalidation_v2.derived_receiver_port_v2h import ReceiverPortV2h
from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import ActorCreditPlanV2l
from spk_backvalidation_v2.derived_causal_admission_v2o import CausalAdmissionPlanV2o
from spk_backvalidation_v2.derived_concurrent_consumer_v2s import (
    DerivedConcurrentConsumer, ConcurrentConsumerPlan, derive_concurrent_executor,
)
from spk_bv_research.three_way_causal_priority_integration_v2r import (
    MODES, validate_v2q,
)
from spk_bv_research.actor_priority_contention_integration_v2m import REGIMES, _payload
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import (
    require, snapshot, source_pins, runtime_modules_bound,
)
from spk_bv_research.coincident_admission_discrimination_v2e import (
    RECIPES, build_workload,
)
from spk_bv_research.link_pressure_v0u import ARMS, _arm
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources
from spk_backvalidation_v2.derived_native_fork_v2g import read_pinned_source

SCHEMA = 'spk-bv-cumulative-source-pinned-concurrent-consumer-arbiter/v2s-v2u'
STATUS = 'DERIVED_TRUE_PRE_FORWARD_PAID_CONSUMER_CAUSAL_ARBITRATION_NATIVE_BLOCKED'
CONTRACT = 'V2S_V2U_SIGNED_V2R_PREDECESSOR_ONLY'
PREDECESSOR_SHA = '731050ab7dc675b073afa9625b1cd378a9a4b7289e51d7f61078af294ba9f279'
INTERVENTIONS = ('pre_service_zero', 'consumer_tail_off',
                 'ACK_credit_zero', 'causal_transport_loss')
EXCLUSIONS = (
    'simultaneous_arbitration_is_separately_compiled_derived_only',
    'no_frozen_native_actor_or_feedback_operator_has_been_modified',
    'ACK_is_independently_PE_memory_paid_and_distinct_from_application',
    'a_resource_only_projection_does_not_repair_changed_forward_or_BV_timing',
    'negative_credit_requires_source_delivered_negative_receiver_judgment',
    'loss_overflow_quota_and_horizon_rejection_are_not_silence_certificates',
    'source_pinned_15_by_3_by_2_matrix_not_universal_workload_parity',
    'abstract_PE_memory_units_not_proven_hardware_cycles',
    'in_process_hash_chains_are_custody_alarms_not_authenticity_proofs',
    'frozen_native_learning_policy_universal_liveness_and_actor_intake_blocked',
)


def validate_v2r(previous, raw):
    require(type(previous) is dict and type(raw) is bytes and canon(previous) == raw
            and sha256(raw).hexdigest() == PREDECESSOR_SHA,
            'v2s-v2u signed predecessor content/sha drift')
    require(previous.get('schema') ==
            'spk-bv-pinned-three-way-causal-priority-discrimination/v2r' and
            previous.get('status') ==
            'DERIVED_THREE_WAY_CAUSAL_GUARD_CONTENTION_DISCRIMINATED_NATIVE_ARBITER_BLOCKED'
            and previous.get('reference_v2q_sha256') ==
                'f214cbe1c75df7535171d14400c2cf37965fa5868aa55d02bc8a56f0891aa926'
            and previous.get('new_native_runs') == 90 and
            previous.get('new_derived_four_guard_runs') == 360 and
            previous.get('new_derived_causal_intervention_runs') == 720 and
            previous.get('native_concurrent_three_way_event_arbitration_proven') is False
            and previous.get('native_forward_credit_learning_contract_proven') is False
            and previous.get('native_operator_updates') == 0 and
            previous.get('next_gate') ==
                'BLOCKED_FROZEN_NATIVE_CONCURRENT_ACTOR_CONSUMER_FORWARD_ARBITRATION',
            'v2s-v2u signed v2r scientific boundary drift')
    totals = previous.get('causal_priority_resource_totals') or {}
    require(all(totals.get(regime, {}).get('strict_native_ready', {}).get(
                    'full_native_projection') == 45 and
                totals[regime]['strict_native_ready']['ACKs'] == 156 and
                totals[regime]['strict_native_ready']['consumer_paid'] == 156
                for regime, _ in REGIMES) and
            previous.get('bounded_horizon_discrimination', {}).get('max_ticks') == 11
            and previous['bounded_horizon_discrimination']['guard_modes'][
                'strict_native_ready'] == 'EXACT_FULL_NATIVE_PROJECTION_AND_PAID_CONSUMER',
            'v2s-v2u prior native/ACK/consumer causal evidence drift')
    rows = previous.get('paired_native_matrix')
    require(type(rows) is list and len(rows) == len(RECIPES),
            'v2s-v2u signed 15 organic workloads missing')
    for (label, recipe), row in zip(RECIPES, rows):
        require(row.get('label') == label and
                row.get('recipe') == [list(x) for x in recipe] and
                [x.get('mode') for x in row.get('modes', [])] ==
                    [a[0] for a in ARMS],
                'v2s-v2u signed source workload order drift')
        for mode in row['modes']:
            for regime, capacity in REGIMES:
                cell = mode.get('capacities', {}).get(regime, {})
                require(cell.get('capacity') == capacity and
                        len(cell.get('signed_v2q_native_sha256', '')) == 64 and
                        set(cell.get('guard_modes', {})) ==
                            {name for name, _, _ in MODES} and
                        cell['guard_modes']['strict_native_ready'][
                            'full_native_projection'] is True,
                        'v2s-v2u signed full 90-cell source matrix drift')
    return True


def _derived_arm(source, native_executor, plan_type, changed, fabric, plans,
                 enabled, priority, digest, data, *, name, forward, bv,
                 intervention='normal'):
    opts = {}
    consumer_plan = ConcurrentConsumerPlan()
    credit_plan = ActorCreditPlanV2l()
    if intervention == 'pre_service_zero':
        consumer_plan = replace(consumer_plan, max_per_tick=0)
    elif intervention == 'consumer_tail_off':
        consumer_plan = replace(consumer_plan, max_tail_ticks=0)
    elif intervention == 'ACK_credit_zero':
        credit_plan = ActorCreditPlanV2l(max_abs_credit=0)
    elif intervention == 'causal_transport_loss':
        opts['accept'] = lambda _: False
    else:
        require(intervention == 'normal', 'v2s-v2u unknown causal intervention')
    port = ReceiverPortV2h(**opts)
    actor = DerivedConcurrentConsumer(port, concurrent_plan=consumer_plan,
        admission_plan=CausalAdmissionPlanV2o(forward, bv), credit_plan=credit_plan)
    observer = CallsiteObserver()
    compiled, _, semantic, resource = derive_concurrent_executor(
        source, native_executor, port, actor, observer)
    captured = {}

    def run(*args, **kwargs):
        captured['derived'] = compiled(*args, **kwargs)
        captured['projected'] = actor.project_original_native_result(
            captured['derived'])
        return captured['projected']

    signed = _arm(run, plan_type, changed, fabric, plans,
                  f'v2s-v2u-{name}-{intervention}', enabled, priority, digest, data)
    summary = actor.summary()
    acks, consumed = actor.credit_journal(), actor.concurrent_journal()
    trace = actor.concurrent_trace()
    require(semantic == (('batch', 194), ('clock', 125),
                         ('emission', 217), ('ingress', 136)) and
            resource == (158, 296, 307) and
            not observer.overflow and not observer.sink_failed and
            observer.counts()['_admit'] == 1 and
            observer.counts()['_admit_plan'] == 1 and
            summary['derived_actor_credit_ack_count'] == len(acks) and
            summary['concurrent_paid_applications'] == len(consumed) and
            summary['concurrent_consumer_PE_units'] == len(consumed) and
            summary['concurrent_consumer_memory_units'] == 2 * len(consumed) and
            summary['concurrent_pending_acks'] == len(acks) - len(consumed) and
            summary['concurrent_before_forward_applications'] +
                summary['concurrent_tail_applications'] == len(consumed) and
            summary['v2q_post_forward_lane_disabled'] is True and
            summary['native_operator_updates'] == 0 and
            summary['frozen_actor_state_changed'] is False and
            summary['absence_certificates'] == 0 and
            len(trace) == summary['native_original_timeline_rows'] +
                summary['concurrent_consumer_tail_rows'],
            'v2s-v2u concurrent source compiler/PE/ACK provenance drift')
    if intervention == 'normal':
        require(len(acks) == len(consumed),
                'v2s-v2u default paid concurrent service left pending ACKs')
    elif intervention == 'pre_service_zero':
        require(not consumed and summary['concurrent_pending_acks'] == len(acks),
                'v2s-v2u zero service fabricated consumed ACK')
    elif intervention == 'consumer_tail_off':
        require(summary['concurrent_consumer_tail_rows'] == 0,
                'v2s-v2u tail-off fabricated resource rows')
    else:
        require(not acks and not consumed and not summary['concurrent_consumer_tail_rows'],
                'v2s-v2u null cause fabricated concurrent actor credit')
    return signed, summary, acks, consumed, trace, captured, port.summary()


def _bounded_horizon(source, case, fabric, plans, native_executor, plan_type):
    reduced = (plans[0], replace(plans[1], fabric_slots_per_tick=1),
               plans[2], plans[3])
    bound = plan_type(max_ticks=11)
    native = native_executor(case, fabric, *reduced, bound)
    require(len(native['resources']['timeline']) == 11,
            'v2s-v2u signed native bounded witness changed')
    outcomes = {}
    for name, forward, bv in MODES:
        port = ReceiverPortV2h()
        actor = DerivedConcurrentConsumer(port,
            admission_plan=CausalAdmissionPlanV2o(forward, bv))
        compiled, _, _, _ = derive_concurrent_executor(
            source, native_executor, port, actor, CallsiteObserver())
        try:
            raw = compiled(case, fabric, *reduced, bound)
        except LiveBVRejected as exc:
            require(name != 'strict_native_ready' and
                    str(exc) == 'bounded live logical horizon exceeded',
                    'v2s-v2u strict mode failed native finite horizon')
            outcomes[name] = 'BOUNDED_HORIZON_REJECTED_NOT_SILENCE_PROOF'
        else:
            require(name == 'strict_native_ready' and
                    actor.project_original_native_result(raw) == native and
                    len(actor.concurrent_journal()) > 0,
                    'v2s-v2u one-sided guard violated source-pinned horizon')
            outcomes[name] = 'EXACT_NATIVE_PARITY_IN_DERIVED_HORIZON'
    return {'max_ticks': 11, 'guard_modes': outcomes,
            'attempts': 5, 'universal_liveness_proven': False}


def _negative_fixture(source, case, fabric, plans, native_executor, plan_type):
    negative = (('ACC', (1, 0)), ('CMP', 100), ('EMIT', 7), ('RESET', 0))
    modified = replace(case, nodes=tuple(replace(node, instructions=negative)
                 if node.node_id == 'B' else node for node in case.nodes))
    reduced = (plans[0], replace(plans[1], fabric_slots_per_tick=1),
               plans[2], plans[3])
    native = native_executor(modified, fabric, *reduced, plan_type())
    port = ReceiverPortV2h()
    actor = DerivedConcurrentConsumer(port)
    compiled, _, _, _ = derive_concurrent_executor(
        source, native_executor, port, actor, CallsiteObserver())
    raw = compiled(modified, fabric, *reduced, plan_type())
    summary = actor.summary()
    receipts = actor.concurrent_journal()
    require(actor.project_original_native_result(raw) == native and
            port.summary()['negative_judgments'] == 2 and
            [r['actor'] for r in receipts] == ['A', 'A'] and
            [r['response'] for r in receipts] == [-1, -1] and
            summary['concurrent_consumer_credit']['A'] == -2 and
            summary['concurrent_consumer_PE_units'] == 2 and
            summary['concurrent_consumer_memory_units'] == 4 and
            summary['native_operator_updates'] == 0,
            'v2s-v2u real negative B violated separate actor ownership')
    return {'real_negative_B_judgments': 2, 'applied_to': 'A',
            'concurrent_credit_A': -2, 'independent_PE_units': 2,
            'independent_memory_units': 4, 'native_learning_observed': False}


def experiment(previous, raw, *, root: Path, fixture_fn, native_executor, plan_type):
    validate_v2r(previous, raw)
    root = root.resolve(strict=True)
    start_pins = source_pins(root)
    start_arch = read_pinned_sources(root)
    runtime_modules_bound(root, native_executor, fixture_fn, plan_type)
    source = read_pinned_source(root)
    case, fabric, plans = fixture_fn()
    input_hash = snapshot((case, fabric, plans))
    totals = {regime: {name: {
        'cells': 0, 'full_native_equal': 0, 'forward_trace_equal': 0,
        'feedback_trace_equal': 0, 'functional_payload_equal': 0,
        'ACKs': 0, 'consumer_paid': 0, 'consumer_before_forward': 0,
        'consumer_tail': 0, 'pending': 0, 'independent_PE_units': 0,
        'independent_memory_units': 0, 'capacity_pressure_ticks': 0,
        'forward_terminal_changed': 0,
    } for name, _, _ in MODES} for regime, _ in REGIMES}
    interventions = {x: {'cells': 0, 'ACKs': 0, 'applied': 0,
                         'before_forward': 0, 'native_restored': 0,
                         'same_forward_as_baseline': 0,
                         'same_feedback_as_baseline': 0,
                         'same_ACK_journal_as_baseline': 0}
                     for x in INTERVENTIONS}
    causal_consumer_witnesses = 0
    cells = []
    for i, (label, recipe) in enumerate(RECIPES):
        altered = build_workload(case, recipe)
        modes = []
        for j, (mode, enabled, priority) in enumerate(ARMS):
            capacities = {}
            for regime, capacity in REGIMES:
                predecessor = previous['paired_native_matrix'][i][
                    'modes'][j]['capacities'][regime]
                amended = (plans[0], replace(plans[1], fabric_slots_per_tick=capacity),
                           plans[2], plans[3])
                data = (altered, fabric, amended)
                digest = snapshot(data)
                raw_original = {}

                def capture(*args, **kwargs):
                    raw_original['result'] = native_executor(*args, **kwargs)
                    return raw_original['result']

                signed_native = _arm(capture, plan_type, altered, fabric, amended,
                    'v2s-v2u-native-'+regime, enabled, priority, digest, data)
                require(signed_native['whole_result_sha256'] ==
                        predecessor['signed_v2q_native_sha256'],
                        'v2s-v2u frozen source SHA differs from signed v2r matrix')
                native = raw_original['result']
                guards = {}
                for name, forward, bv in MODES:
                    signed, summary, acks, paid, trace, captured, feedback = _derived_arm(
                        source, native_executor, plan_type, altered, fabric,
                        amended, enabled, priority, digest, data,
                        name=name, forward=forward, bv=bv)
                    projected = captured['projected']
                    whole = projected == native
                    forward_equal = projected['forward'] == native['forward']
                    feedback_equal = projected['feedback'] == native['feedback']
                    functional = _payload(projected['forward']) == _payload(native['forward'])
                    require(functional and len(acks) == len(paid) and
                            (name != 'strict_native_ready' or
                             (whole and forward_equal and feedback_equal and
                              len(acks) == predecessor['guard_modes'][name]['ACKs'])),
                            f'v2s-v2u derived schedule drift {label}/{mode}/{regime}/{name}: '
                            f'functional={functional} acks={len(acks)} paid={len(paid)} '
                            f'whole={whole} fwd={forward_equal} bv={feedback_equal}')
                    agg = totals[regime][name]
                    agg['cells'] += 1
                    agg['full_native_equal'] += int(whole)
                    agg['forward_trace_equal'] += int(forward_equal)
                    agg['feedback_trace_equal'] += int(feedback_equal)
                    agg['functional_payload_equal'] += int(functional)
                    agg['ACKs'] += len(acks)
                    agg['consumer_paid'] += len(paid)
                    agg['consumer_before_forward'] += summary['concurrent_before_forward_applications']
                    agg['consumer_tail'] += summary['concurrent_tail_applications']
                    agg['pending'] += summary['concurrent_pending_acks']
                    agg['independent_PE_units'] += len(paid)
                    agg['independent_memory_units'] += 2 * len(paid)
                    agg['capacity_pressure_ticks'] += summary['concurrent_capacity_pressure_ticks']
                    agg['forward_terminal_changed'] += int([
                        x['timestamp'] for x in projected['forward']['terminal']] !=
                        [x['timestamp'] for x in native['forward']['terminal']])
                    cell = {
                        'full_native_equal': whole,
                        'forward_trace_equal': forward_equal,
                        'feedback_trace_equal': feedback_equal,
                        'functional_payload_equal': functional,
                        'ACKs': len(acks), 'consumer_paid': len(paid),
                        'consumer_pre_forward': summary['concurrent_before_forward_applications'],
                        'consumer_tail': summary['concurrent_tail_applications'],
                        'capacity_pressure_ticks': summary['concurrent_capacity_pressure_ticks'],
                        'consumer_receipt_chain_root': summary['concurrent_last_chain_digest'],
                        'resource_timeline_sha256': sha256(canon(
                            captured['derived']['resources']['timeline'])).hexdigest(),
                        'native_forward_terminal_ticks': [x['timestamp'] for x in
                            native['forward']['terminal']],
                        'derived_forward_terminal_ticks': [x['timestamp'] for x in
                            projected['forward']['terminal']],
                    }
                    if regime == 'contended_capacity' and name == 'actor_first_null_guard':
                        for intervention in INTERVENTIONS:
                            _, alt_s, alt_acks, alt_paid, _, alt_raw, _ = _derived_arm(
                                source, native_executor, plan_type, altered, fabric,
                                amended, enabled, priority, digest, data, name=name,
                                forward=forward, bv=bv, intervention=intervention)
                            candidate = alt_raw['projected']
                            counter = interventions[intervention]
                            counter['cells'] += 1
                            counter['ACKs'] += len(alt_acks)
                            counter['applied'] += len(alt_paid)
                            counter['before_forward'] += alt_s['concurrent_before_forward_applications']
                            counter['native_restored'] += int(candidate == native)
                            counter['same_forward_as_baseline'] += int(
                                candidate['forward'] == projected['forward'])
                            counter['same_feedback_as_baseline'] += int(
                                candidate['feedback'] == projected['feedback'])
                            counter['same_ACK_journal_as_baseline'] += int(alt_acks == acks)
                            if intervention == 'pre_service_zero':
                                require(not alt_paid and
                                        alt_s['concurrent_pending_acks'] == len(alt_acks),
                                        'v2s-v2u zero consumer charged phantom ACK')
                                if candidate['forward'] != projected['forward']:
                                    causal_consumer_witnesses += 1
                            elif intervention == 'consumer_tail_off':
                                require(candidate == projected and alt_acks == acks,
                                        'v2s-v2u tail-only service changes prior native schedule')
                            else:
                                require(candidate == native and not alt_acks and
                                        not alt_paid, 'v2s-v2u causal null did not restore native')
                        cell['causal_interventions_checked'] = list(INTERVENTIONS)
                    guards[name] = cell
                capacities[regime] = {
                    'capacity': capacity,
                    'signed_v2r_native_sha256': predecessor['signed_v2q_native_sha256'],
                    'guard_modes': guards,
                }
            modes.append({'mode': mode, 'capacities': capacities})
        cells.append({'label': label, 'recipe': [list(x) for x in recipe],
                      'modes': modes})
        require(snapshot((case, fabric, plans)) == input_hash,
                'v2s-v2u fixture input was mutated by derived compiler')
    negative = _negative_fixture(source, case, fabric, plans, native_executor, plan_type)
    horizon = _bounded_horizon(source, case, fabric, plans, native_executor, plan_type)
    require(all(v['cells'] == 45 and v['functional_payload_equal'] == 45 and
                v['ACKs'] == 156 and v['consumer_paid'] == 156 and
                v['independent_PE_units'] == 156 and
                v['independent_memory_units'] == 312
                for byregime in totals.values() for v in byregime.values()) and
            all(totals[r]['strict_native_ready']['full_native_equal'] == 45
                for r, _ in REGIMES) and
            totals['contended_capacity']['strict_native_ready']['consumer_before_forward'] == 0 and
            totals['contended_capacity']['actor_first_null_guard']['consumer_before_forward'] > 0 and
            all(v['cells'] == 45 for v in interventions.values()) and
            interventions['ACK_credit_zero']['native_restored'] == 45 and
            interventions['causal_transport_loss']['native_restored'] == 45 and
            interventions['pre_service_zero']['applied'] == 0 and
            interventions['consumer_tail_off']['same_forward_as_baseline'] == 45 and
            causal_consumer_witnesses > 0 and
            horizon['guard_modes']['strict_native_ready'] ==
                'EXACT_NATIVE_PARITY_IN_DERIVED_HORIZON' and
            source_pins(root) == start_pins and
            read_pinned_sources(root) == start_arch and
            read_pinned_source(root) == source and
            snapshot((case, fabric, plans)) == input_hash,
            'v2s-v2u cumulative concurrent causal/resource/horizon gate incomplete')
    return {'paired_native_matrix': cells,
            'three_way_paid_resource_totals': totals,
            'intervention_totals': interventions,
            'causal_consumer_forward_witness_cells': causal_consumer_witnesses,
            'negative_fixture': negative,
            'bounded_horizon_witness': horizon,
            'native_original_runs': 90,
            'derived_three_way_guard_runs': 360,
            'derived_causal_intervention_runs': 180,
            'negative_fixture_runs': 2,
            'bounded_horizon_execution_attempts': 5,
            'source_custody': True}


def build_report(previous, raw, result=None):
    validate_v2r(previous, raw)
    require(result is None or
            (result['source_custody'] and result['native_original_runs'] == 90 and
             result['derived_three_way_guard_runs'] == 360 and
             result['derived_causal_intervention_runs'] == 180 and
             result['causal_consumer_forward_witness_cells'] > 0),
            'v2s-v2u source-replayed cumulative arbitration gate missing')
    return {
        'schema': SCHEMA,
        'status': STATUS if result else CONTRACT,
        'reference_v2r_sha256': sha256(raw).hexdigest(),
        'cumulative_research_stages': [
            'v2s-source-compiled-real-pre-forward-independent-consumer-service',
            'v2t-three-way-PE-RAM-contention-and-causal-negative-controls',
            'v2u-adversarial-exact-projection-bounded-horizon-and-science-boundary',
        ],
        'source_pins_rechecked': bool(result),
        'new_native_runs': result['native_original_runs'] if result else 0,
        'new_derived_three_way_guard_runs': (
            result['derived_three_way_guard_runs'] if result else 0),
        'new_derived_causal_intervention_runs': (
            result['derived_causal_intervention_runs'] if result else 0),
        'new_negative_fixture_runs': result['negative_fixture_runs'] if result else 0,
        'new_bounded_horizon_execution_attempts': (
            result['bounded_horizon_execution_attempts'] if result else 0),
        'causal_consumer_forward_witness_cells': (
            result['causal_consumer_forward_witness_cells'] if result else 0),
        'three_way_paid_resource_totals': (
            result['three_way_paid_resource_totals'] if result else None),
        'intervention_totals': result['intervention_totals'] if result else None,
        'negative_fixture': result['negative_fixture'] if result else None,
        'bounded_horizon_witness': (
            result['bounded_horizon_witness'] if result else None),
        'paired_native_matrix': result['paired_native_matrix'] if result else None,
        'independent_derived_pre_forward_actor_consumer_proven': bool(result),
        'frozen_native_concurrent_three_way_arbiter_proven': False,
        'frozen_native_actor_learning_contract_proven': False,
        'universal_finite_forward_liveness_proven': False,
        'native_operator_updates': 0,
        'next_gate': 'BLOCKED_EXPLICIT_FROZEN_NATIVE_ACTOR_SERVICE_AND_LEARNING_CONTRACT',
        'claims_excluded': list(EXCLUSIONS),
    }
