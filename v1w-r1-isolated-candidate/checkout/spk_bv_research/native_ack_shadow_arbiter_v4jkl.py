"""BV v4j-v4l: *shadow* ACK service-slot arbitration over signed native traces.

The only executed neuron is the unchanged native v0e source. A candidate ACK
slot can either use truly spare native PE/O/E budget or hypothetically displace
one specifically identified native forward/BV PE service. Displaced services
are recorded as UNSCHEDULED_DEBT: no fake completion, causal replay, original
timing parity or real ACK credit is claimed. Source readiness is exogenous.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import replace
from hashlib import sha256

from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    LiveBVPlanV0e, execute_live_v0e,
)
from spk_bv_research.native_actor_capacity_envelope_v4def import (
    EnvelopeRejected, check_v4_source, native_headroom,
)
from spk_bv_research.native_actor_coverage_frontier_v4ghi import (
    STATUS as FRONTIER_STATUS, WINDOWS, window_audit,
)
from spk_bv_research.native_actor_service_contract_candidate_v4abc import source_row_gaps
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import snapshot
from spk_bv_research.grant_rank_integration_v3tuv import (
    NEW_SCHEDULES, ARMS, CAPACITIES, POLICIES, QUOTAS,
)
from search.spk_bv_v0e_live_evidence import fixture

SCHEMA = 'spk-bv-native-ACK-shadow-resource-arbiter/research-v4j-v4l'
STATUS = 'COUNTERFACTUAL_NATIVE_SLOT_ARBITER_NO_CAUSAL_REEXECUTION'
FRONTIER_REPORT_SHA = 'ad94dcfe5513da0f93b8e81daf84eead84617409dfa5b72fc758982ee2df2c32'
PREV_REPORT_SHA = 'fdc4335bbb42e145319ec266c3d893348026d617f05a1c5b8383c5caab426a03'
OWNER = 'PE0'
STRATEGIES = ('deadline-only', 'opportunistic-spare')
DONOR_PREFERENCES = ('protect-forward', 'protect-BV')


def require(ok, message):
    if not ok:
        raise EnvelopeRejected(message)


def native_service_tokens(native, owner_by_node):
    """Reconcile EVERY typed native PE service to source per-tick PE totals."""
    require(type(native) is dict and type(owner_by_node) is dict,
            'v4j missing native source or node ownership')
    timeline = native['resources']['timeline']
    by_tick = defaultdict(list)
    identities = set()
    for index, batch in enumerate(native['forward']['batches'], 1):
        node = batch['node']
        require(node in owner_by_node, 'v4j forward batch lost PE owner')
        identity = 'forward-batch-%04d' % index
        by_tick[batch['tick']].append({
            'identity': identity, 'kind': 'forward', 'pe': owner_by_node[node],
            'node': node, 'parents': list(batch['parents']),
            'source_original_tick': batch['tick'],
        })
        identities.add(identity)
    for grant in native['feedback']['link_grants']:
        identity = 'native-BV-'+grant['packet_id']
        require(identity not in identities, 'v4j native BV packet identity overlap')
        by_tick[grant['tick']].append({
            'identity': identity, 'kind': 'BV', 'pe': grant['source_pe'],
            'node': grant['sender'], 'parents': list(),
            'source_original_tick': grant['tick'],
        })
        identities.add(identity)
    for tick in timeline:
        operators = by_tick[tick['tick']]
        counted = Counter(op['pe'] for op in operators)
        require(dict(sorted(counted.items())) == tick['pe_service_by_pe'] and
                sum(counted.values()) == tick['pe_service_total'] and
                sum(op['kind'] == 'forward' for op in operators) ==
                tick['forward_computations'] and
                sum(op['kind'] == 'BV' for op in operators) ==
                tick['feedback_sends'],
                'v4j source typed operation/PE resource mismatch')
    require(len(identities) == sum(t['pe_service_total'] for t in timeline) and
            all(tick in {t['tick'] for t in timeline} for tick in by_tick),
            'v4j unmatched, duplicate or off-horizon native service')
    return {tick['tick']: tuple(by_tick[tick['tick']]) for tick in timeline}


def candidate_slot(tick, operations, *, global_cap, owner_cap,
                   owner_memory_cap, total_memory_cap, O_cap, E_cap,
                   allow_PE_reassign, donor_preference):
    """Conservative single synthetic ACK slot; no actual displacement occurs.

    Memory is charged *without* reclaiming donor memory, intentionally. If
    this fails, we cannot say a different versioned scheduler could not work;
    only that this signed-source conservative resource witness is unavailable.
    """
    require(type(allow_PE_reassign) is bool and donor_preference in
            DONOR_PREFERENCES and type(operations) in (tuple, list),
            'v4k invalid arbiter controls')
    h = native_headroom(
        tick, global_cap=global_cap, owner_cap=owner_cap,
        owner_memory_cap=owner_memory_cap,
        total_memory_cap=total_memory_cap, O_cap=O_cap, E_cap=E_cap)
    if not h['O_E_memory_free']:
        return {'accepted': False, 'reason': 'O_E_MEMORY_NOT_PROVEN', 'donor': None,
                'slot_kind': None}
    if h['all_free']:
        return {'accepted': True, 'reason': 'NATIVE_SPARE', 'donor': None,
                'slot_kind': 'spare'}
    if not allow_PE_reassign:
        return {'accepted': False, 'reason': 'UNAUTHORIZED_PE_REASSIGN',
                'donor': None, 'slot_kind': None}
    require(all(type(op) is dict and op.get('kind') in ('forward', 'BV') and
                type(op.get('pe')) is str and type(op.get('identity')) is str
                for op in operations), 'v4k malformed typed donor')
    # If the owner PE is full, only a PE0 donor can free its service budget.
    eligible = [op for op in operations if h['owner_PE_free'] or op['pe'] == OWNER]
    if not eligible:
        return {'accepted': False, 'reason': 'NO_IDENTIFIABLE_NATIVE_DONOR',
                'donor': None, 'slot_kind': None}
    first_kind = 'BV' if donor_preference == 'protect-forward' else 'forward'
    donor = min(eligible, key=lambda op: (op['kind'] != first_kind,
                                         op['source_original_tick'], op['identity']))
    after_global = tick['pe_service_total'] - 1 + 1
    after_owner = tick['pe_service_by_pe'].get(OWNER, 0) - (donor['pe'] == OWNER) + 1
    require(after_global <= global_cap and after_owner <= owner_cap,
            'v4k proposed donor insufficient to free owner/global PE')
    return {'accepted': True, 'reason': 'CONDITIONAL_PE_DISPLACEMENT',
            'donor': dict(donor), 'slot_kind': 'preempted-native-PE'}


def arbitrate_fixed_source(rows, timeline, operations, *, window, strategy,
                           allow_PE_reassign, donor_preference,
                           global_cap, owner_cap, owner_memory_cap,
                           total_memory_cap, O_cap, E_cap):
    """Online deterministic shadow choice on an immutable exogenous trace.

    Does not look forward at future native ticks. A selected PE donor becomes
    open *causal* debt and is never pretended to have completed later.
    """
    source_row_gaps(rows)
    require(type(window) is int and window in WINDOWS and strategy in STRATEGIES
            and len(rows) == len(timeline) and
            all(rows[i]['tick'] == timeline[i]['tick'] for i in range(len(rows))),
            'v4k source/native ticks or controls invalid')
    reservations = []
    denials = []
    missing_windows = []
    run_start = last_reserved = None
    for i, row in enumerate(rows):
        tick = row['tick']
        pending_no_grant = (row['ready_control_count'] > 0 and
                            row['grant_prefix_count'] == 0)
        if not pending_no_grant:
            run_start = last_reserved = None
            continue
        if run_start is None:
            run_start = tick
        since = (tick - last_reserved if last_reserved is not None else
                 tick - run_start + 1)
        due = since >= window
        h = native_headroom(timeline[i], global_cap=global_cap,
                            owner_cap=owner_cap,
                            owner_memory_cap=owner_memory_cap,
                            total_memory_cap=total_memory_cap, O_cap=O_cap, E_cap=E_cap)
        early = (strategy == 'opportunistic-spare' and h['all_free'] and
                 since >= max(1, window//2))
        if not (due or early):
            continue
        event = candidate_slot(
            timeline[i], operations[tick], global_cap=global_cap,
            owner_cap=owner_cap, owner_memory_cap=owner_memory_cap,
            total_memory_cap=total_memory_cap, O_cap=O_cap, E_cap=E_cap,
            allow_PE_reassign=allow_PE_reassign,
            donor_preference=donor_preference)
        if event['accepted']:
            reservations.append({'tick': tick, 'slot_kind': event['slot_kind'],
                                 'would_defer_native': event['donor'],
                                 'source_ACK_payload_delivered': False})
            last_reserved = tick
        else:
            denials.append({'tick': tick, 'reason': event['reason']})
    chosen = {r['tick'] for r in reservations}
    for i in range(len(rows)-window+1):
        block = rows[i:i+window]
        if (all(r['ready_control_count'] > 0 and
                r['grant_prefix_count'] == 0 for r in block) and
            not any(r['tick'] in chosen for r in block)):
            missing_windows.append([block[0]['tick'], block[-1]['tick']])
    debt = [r['would_defer_native'] for r in reservations
            if r['would_defer_native'] is not None]
    require(len({(x['source_original_tick'], x['identity']) for x in debt}) == len(debt)
            and all(x['kind'] in ('forward', 'BV') for x in debt) and
            (not debt or allow_PE_reassign),
            'v4k repeated native service debt or unauthorized displacement')
    return {
        'strategy': strategy,
        'admission': 'PE_REASSIGN_CONDITIONAL_MEMORY_GUARD' if allow_PE_reassign
                     else 'NATIVE_SPARE_ONLY',
        'donor_preference': donor_preference if allow_PE_reassign else None,
        'window_ticks': window,
        'synthetic_service_reservations': len(reservations),
        'unchanged_native_spare_reservations': len(reservations)-len(debt),
        'would_displace_native_service_units': len(debt),
        'would_displace_forward_units': sum(x['kind'] == 'forward' for x in debt),
        'would_displace_BV_units': sum(x['kind'] == 'BV' for x in debt),
        'denied_reservation_attempts': len(denials),
        'missing_full_source_windows': len(missing_windows),
        'complete_source_window_coverage': not missing_windows,
        'first_missing_source_window': missing_windows[0] if missing_windows else None,
        'first_denied_reservation': denials[0] if denials else None,
        'reservation_ledger': reservations,
        'native_service_debt_ledger': debt,
        'native_service_debt_reexecuted': False,
        'forward_or_BV_causal_timing_recomputed': False,
        'real_actor_ACK_deliveries': 0,
    }


def evaluate(v3, raw3, v4, raw4, v4d, raw4d, v4g, raw4g, *,
             fixture_fn=fixture, native_executor=execute_live_v0e):
    check_v4_source(v3, raw3, v4, raw4)
    require(type(v4d) is dict and type(raw4d) is bytes and
            canon(v4d) == raw4d and sha256(raw4d).hexdigest() == PREV_REPORT_SHA
            and v4d.get('native_v0e_modified') is False and
            type(v4g) is dict and type(raw4g) is bytes and canon(v4g) == raw4g
            and sha256(raw4g).hexdigest() == FRONTIER_REPORT_SHA and
            v4g.get('status') == FRONTIER_STATUS and
            v4g.get('signed_v4def_sha256') == PREV_REPORT_SHA and
            v4g.get('native_v0e_modified') is False and
            v4g.get('reserved_native_ACK_arbiter_implemented') is False,
            'v4j signed v4d/v4g preadmission frontier not available')
    native_runs = native_ticks = typed_native_units = contexts = 0
    rows_out = []
    rollups = {}
    for window in WINDOWS:
        for strategy in STRATEGIES:
            for mode, prefs in (('NATIVE_SPARE_ONLY', (DONOR_PREFERENCES[0],)),
                                ('PE_REASSIGN_CONDITIONAL_MEMORY_GUARD', DONOR_PREFERENCES)):
                for pref in prefs:
                    name = f'W{window}/{strategy}/{mode}/{pref if mode != "NATIVE_SPARE_ONLY" else "none"}'
                    rollups[name] = {'window_ticks': window, 'strategy': strategy,
                                     'admission': mode,
                                     'donor_preference': pref if mode != 'NATIVE_SPARE_ONLY' else None,
                                     'contexts': 0, 'contexts_with_complete_coverage': 0,
                                     'contexts_with_missing_windows': 0,
                                     'synthetic_reservations': 0,
                                     'native_service_units_would_be_displaced': 0,
                                     'native_forward_units_would_be_displaced': 0,
                                     'native_BV_units_would_be_displaced': 0,
                                     'denied_reservation_attempts': 0,
                                     'missing_full_source_windows': 0,
                                     'first_preempted_native_service': None,
                                     'first_missing_source_window_case': None}
    require(len(v3['source_matrix']) == len(NEW_SCHEDULES) == 3,
            'v4j source schedule count changed')
    for source, (schedule, ticks) in zip(v3['source_matrix'], NEW_SCHEDULES):
        require(source['schedule'] == schedule and source['source_external_ticks'] == list(ticks),
                'v4j signed source schedule identity mismatch')
        case, fabric, plans = fixture_fn(ticks=ticks)
        owners = {placement.node_id: placement.pe_id for placement in fabric.placement}
        require(owners.get('A') == OWNER, 'v4j native actor owner moved')
        for mode, (label, enabled, priority) in zip(source['modes'], ARMS):
            require(mode['mode'] == label, 'v4j native mode source mismatch')
            for cap_record, cap in zip(mode['capacities'], CAPACITIES):
                require(cap_record['native_PE_capacity'] == cap,
                        'v4j signed global PE budget mismatch')
                pplan = replace(plans[1], fabric_slots_per_tick=cap)
                native = native_executor(case, fabric, plans[0], pplan,
                                         plans[2], plans[3],
                                         LiveBVPlanV0e(enabled=enabled, priority=priority))
                require(snapshot(native) == cap_record['original_native_sha256'],
                        'v4j mutated frozen source native execution')
                timeline = native['resources']['timeline']
                operations = native_service_tokens(native, owners)
                native_runs += 1
                native_ticks += len(timeline)
                typed_native_units += sum(len(v) for v in operations.values())
                mem = plans[2]
                memory_domains = dict(mem.domain_slots)
                shared = {'global_cap': cap, 'owner_cap': dict(pplan.pe_slots)[OWNER],
                          'owner_memory_cap': dict(mem.pe_slots)[OWNER],
                          'total_memory_cap': mem.fabric_slots_per_tick,
                          'O_cap': memory_domains['O'], 'E_cap': memory_domains['E']}
                for policy in POLICIES:
                    for quota in QUOTAS:
                        rows = cap_record['derived_policies'][policy][str(quota)][
                            'rank_audit']['per_tick_fifo_prefix']
                        require(len(rows) == len(timeline) and all(
                            rows[i]['tick'] == timeline[i]['tick'] for i in range(len(rows))),
                            'v4j signed source ACK/native tick mismatch')
                        contexts += 1
                        summary = {'schedule': schedule, 'mode': label,
                                   'native_global_PE_capacity': cap,
                                   'policy': policy, 'ACK_quota': quota,
                                   'variants': {}}
                        for name, aggregate in rollups.items():
                            result = arbitrate_fixed_source(
                                rows, timeline, operations,
                                window=aggregate['window_ticks'],
                                strategy=aggregate['strategy'],
                                allow_PE_reassign=aggregate['admission'] != 'NATIVE_SPARE_ONLY',
                                donor_preference=aggregate['donor_preference'] or DONOR_PREFERENCES[0],
                                **shared)
                            # Every source context is the same signed native
                            # trace as v4g; exact count remains an invariant.
                            zero_windows = window_audit(rows, tuple(native_headroom(
                                t, global_cap=cap,
                                owner_cap=shared['owner_cap'],
                                owner_memory_cap=shared['owner_memory_cap'],
                                total_memory_cap=shared['total_memory_cap'],
                                O_cap=shared['O_cap'], E_cap=shared['E_cap'])['all_free']
                                for t in timeline), aggregate['window_ticks'])
                            require(result['missing_full_source_windows'] <=
                                    zero_windows['complete_zero_grant_windows'],
                                    'v4j impossible negative source window count')
                            summary['variants'][name] = result
                            aggregate['contexts'] += 1
                            aggregate['contexts_with_complete_coverage'] += int(
                                result['complete_source_window_coverage'])
                            aggregate['contexts_with_missing_windows'] += int(
                                not result['complete_source_window_coverage'])
                            for target, source_key in (
                                ('synthetic_reservations', 'synthetic_service_reservations'),
                                ('native_service_units_would_be_displaced',
                                 'would_displace_native_service_units'),
                                ('native_forward_units_would_be_displaced',
                                 'would_displace_forward_units'),
                                ('native_BV_units_would_be_displaced', 'would_displace_BV_units'),
                                ('denied_reservation_attempts', 'denied_reservation_attempts'),
                                ('missing_full_source_windows', 'missing_full_source_windows')):
                                aggregate[target] += result[source_key]
                            if (aggregate['first_preempted_native_service'] is None and
                                result['native_service_debt_ledger']):
                                aggregate['first_preempted_native_service'] = {
                                    'schedule': schedule, 'mode': label,
                                    'native_global_PE_capacity': cap,
                                    'policy': policy, 'ACK_quota': quota,
                                    'donor': result['native_service_debt_ledger'][0]}
                            if (aggregate['first_missing_source_window_case'] is None and
                                result['first_missing_source_window'] is not None):
                                aggregate['first_missing_source_window_case'] = {
                                    'schedule': schedule, 'mode': label,
                                    'native_global_PE_capacity': cap,
                                    'policy': policy, 'ACK_quota': quota,
                                    'window_inclusive_ticks': result['first_missing_source_window']}
                        rows_out.append(summary)
    require(native_runs == 18 and contexts == len(rows_out) == 72 and
            native_ticks == 640 and typed_native_units > 0 and
            all(x['contexts'] == 72 and
                x['contexts_with_complete_coverage'] +
                x['contexts_with_missing_windows'] == 72 and
                x['native_forward_units_would_be_displaced'] +
                x['native_BV_units_would_be_displaced'] ==
                x['native_service_units_would_be_displaced']
                for x in rollups.values()),
            'v4j source native/actor shadow conservation failed')
    return {
        'schema': SCHEMA, 'status': STATUS,
        'signed_v3tuv_sha256': sha256(raw3).hexdigest(),
        'signed_v4abc_sha256': sha256(raw4).hexdigest(),
        'signed_v4def_sha256': sha256(raw4d).hexdigest(),
        'signed_v4ghi_sha256': sha256(raw4g).hexdigest(),
        'source_original_native_replays': native_runs,
        'source_original_native_ticks': native_ticks,
        'source_typed_native_service_units': typed_native_units,
        'source_derived_ACK_contexts': contexts,
        'shadow_variants': rollups,
        'source_contexts': rows_out,
        'limitations': [
            'shadow input is fixed original readiness, not feedback after synthetic ACK service',
            'online slot opportunity has no actual receiver credit, BV delivery or FIFO acknowledgment',
            'reassigned PE donor is typed native work recorded as unresolved causal debt',
            'native debt reexecution, link rescheduling, future memory and state causality are absent',
            'memory admission conservatively adds O/E without releasing donor memory',
            'coverage within original finite horizon does not prove deadlines beyond it',
            'synthetic reserved slot is not a native grant or an admitted architecture contract',
            '72 related derived scenarios are not 72 independent real workloads',
        ],
        'native_v0e_modified': False,
        'actual_native_scheduler_rearbitration_implemented': False,
        'native_forward_completion_latency_measured': False,
        'native_actor_learning_implemented': False,
        'next_gate': 'VERSIONED_CAUSAL_NATIVE_REEXECUTION_AND_OWNER_LINK_CREDIT_ADMISSION_REQUIRED',
    }
