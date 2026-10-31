"""BV v4g-v4i: exact bounded ACK *opportunity coverage*, not a scheduler.

For each contiguous source-ready/no-grant run, solve the finite interval
stabbing problem: hypothetically cover every complete W-tick no-grant window
with at least one candidate service tick. Native free slots are observed, while
occupied slots remain only optimistic non-spare candidates. The computation
does NOT consume/alter source ACK queues or prove an ACK admission protocol.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256

from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVPlanV0e, execute_live_v0e
from spk_bv_research.native_actor_capacity_envelope_v4def import (
    EnvelopeRejected, STATUS as PREVIOUS_STATUS, check_v4_source,
    native_headroom,
)
from spk_bv_research.native_actor_service_contract_candidate_v4abc import source_row_gaps
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import snapshot
from spk_bv_research.grant_rank_integration_v3tuv import (
    NEW_SCHEDULES, ARMS, CAPACITIES, POLICIES, QUOTAS,
)
from search.spk_bv_v0e_live_evidence import fixture

SCHEMA = 'spk-bv-source-native-ACK-cover-frontier/research-v4g-v4i'
STATUS = 'EXACT_FINITE_COVERAGE_ONLY_NO_NATIVE_RESERVATION_OR_LIVENESS'
PREVIOUS_REPORT_SHA = 'fdc4335bbb42e145319ec266c3d893348026d617f05a1c5b8383c5caab426a03'
WINDOWS = (2, 4, 8)
OWNER = 'PE0'


def require(condition, reason):
    if not condition:
        raise EnvelopeRejected(reason)


def ready_runs(rows, spare):
    """Contiguous source-ready/no-grant periods, split at real grant ticks."""
    source_row_gaps(rows)
    require(type(spare) in (tuple, list) and len(spare) == len(rows) and
            all(type(x) is bool for x in spare), 'v4g invalid native spare mask')
    runs = []
    start = None
    for i, row in enumerate(rows):
        pending = row['ready_control_count'] > 0 and row['grant_prefix_count'] == 0
        if pending and start is None:
            start = i
        if not pending and start is not None:
            runs.append((start, i, tuple(spare[start:i])))
            start = None
    if start is not None:
        runs.append((start, len(rows), tuple(spare[start:])))
    return runs


def cover_dp(spare, window, *, restrict_to_spare, nonspare_first=False):
    """Exact interval coverage with deterministic lexicographic optimum.

    Optimize minimal placements, tie-breaking on non-spare count, or invert
    their order. The state tracks last selected distance, capped at W. All
    *complete* sliding W-windows must contain a selected tick. No promise is
    made about horizons shorter than W or any unobserved future continuation.
    """
    require(type(spare) in (tuple, list) and all(type(s) is bool for s in spare) and
            type(window) is int and 1 <= window <= 64 and
            type(restrict_to_spare) is bool and type(nonspare_first) is bool,
            'v4g cover invalid type/window')
    length = len(spare)
    require(length <= 128, 'v4g cover unbounded source horizon')
    states = {window: (0, 0, ())}  # distance -> (slots, nonspare, chosen indices)
    for i in range(length):
        next_states = {}
        for elapsed, (slots, nonspare, choices) in states.items():
            # Choose no hypothetical ACK coverage on this tick.
            skipped = min(window, elapsed + 1)
            if i < window - 1 or skipped < window:
                incumbent = next_states.get(skipped)
                candidate = (slots, nonspare, choices)
                if incumbent is None or _rank(candidate, nonspare_first) < _rank(incumbent, nonspare_first):
                    next_states[skipped] = candidate
            # Cover the tick, with an unchanged-native slot or optimistic contention.
            if spare[i] or not restrict_to_spare:
                candidate = (slots + 1, nonspare + (not spare[i]), choices + (i,))
                incumbent = next_states.get(0)
                if incumbent is None or _rank(candidate, nonspare_first) < _rank(incumbent, nonspare_first):
                    next_states[0] = candidate
        states = next_states
    if not states:
        return None
    best = min(states.values(), key=lambda item: _rank(item, nonspare_first))
    return {'placements': best[0], 'nonspare': best[1],
            'local_indices': list(best[2])}


def _rank(candidate, nonspare_first):
    return ((candidate[1], candidate[0], candidate[2]) if nonspare_first
            else (candidate[0], candidate[1], candidate[2]))


def window_audit(rows, spare, window):
    """Exact per-context frontier and first verifiable no-native-slot witness."""
    runs = ready_runs(rows, spare)
    total = {'pending_runs': len(runs), 'complete_zero_grant_windows': 0,
             'windows_without_any_native_spare': 0,
             'unrestricted_minimum_cover_slots': 0,
             'unrestricted_minimum_cover_nonspare': 0,
             'optimistic_minimum_nonspare': 0,
             'optimistic_minimum_nonspare_slots': 0,
             'strict_spare_only_feasible': True,
             'strict_minimum_cover_slots': 0,
             'first_no_spare_window': None,
             'first_strict_infeasibility_witness': None,
             'short_run_ticks_without_complete_window': 0}
    for start, end, mask in runs:
        length = end - start
        if length < window:
            total['short_run_ticks_without_complete_window'] += length
            continue
        total['complete_zero_grant_windows'] += length - window + 1
        first_in_run = None
        for i in range(length-window+1):
            if not any(mask[i:i+window]):
                total['windows_without_any_native_spare'] += 1
                if first_in_run is None:
                    first_in_run = [rows[start+i]['tick'], rows[start+i+window-1]['tick']]
                if total['first_no_spare_window'] is None:
                    total['first_no_spare_window'] = first_in_run
        minimum_cover = cover_dp(mask, window, restrict_to_spare=False)
        minimum_nonspare = cover_dp(mask, window, restrict_to_spare=False,
                                    nonspare_first=True)
        strict_cover = cover_dp(mask, window, restrict_to_spare=True)
        require(minimum_cover is not None and minimum_nonspare is not None and
                (strict_cover is None) == (first_in_run is not None),
                'v4g inconsistent exact interval coverage / native spare witness')
        require(minimum_cover['placements'] == length//window and
                minimum_cover['placements'] <= minimum_nonspare['placements'] and
                minimum_nonspare['nonspare'] <= minimum_cover['nonspare'],
                'v4g exact interval lower bound or optimization invalid')
        total['unrestricted_minimum_cover_slots'] += minimum_cover['placements']
        total['unrestricted_minimum_cover_nonspare'] += minimum_cover['nonspare']
        total['optimistic_minimum_nonspare'] += minimum_nonspare['nonspare']
        total['optimistic_minimum_nonspare_slots'] += minimum_nonspare['placements']
        if strict_cover is None:
            total['strict_spare_only_feasible'] = False
            total['strict_minimum_cover_slots'] = None
            if total['first_strict_infeasibility_witness'] is None:
                total['first_strict_infeasibility_witness'] = first_in_run
        elif total['strict_spare_only_feasible']:
            total['strict_minimum_cover_slots'] += strict_cover['placements']
        require(minimum_nonspare['nonspare'] == 0 if strict_cover is not None else
                minimum_nonspare['nonspare'] > 0,
                'v4g native exact feasibility/optimistic conflict mismatch')
    return total


def evaluate(v3, raw3, v4, raw4, prev, rawprev, *, fixture_fn=fixture,
             native_executor=execute_live_v0e):
    check_v4_source(v3, raw3, v4, raw4)
    require(type(prev) is dict and type(rawprev) is bytes and
            canon(prev) == rawprev and sha256(rawprev).hexdigest() == PREVIOUS_REPORT_SHA and
            prev.get('status') == PREVIOUS_STATUS and
            prev.get('any_reserved_service_contract_implemented') is False and
            prev.get('any_native_actor_liveness_or_learning_proven') is False,
            'v4g exact frontier requires unchanged signed native capacity report')
    observed = prev['source_native_observed_capacity']
    result = {str(w): {'window_ticks': w, 'source_contexts': 0,
                       'strict_spare_only_feasible_contexts': 0,
                       'strict_spare_only_infeasible_contexts': 0,
                       'source_pending_runs': 0,
                       'complete_zero_grant_windows': 0,
                       'windows_without_any_native_spare': 0,
                       'unrestricted_minimum_cover_slots': 0,
                       'unrestricted_minimum_cover_nonspare': 0,
                       'optimistic_minimum_nonspare': 0,
                       'optimistic_minimum_nonspare_slots': 0,
                       'feasible_strict_minimum_cover_slots': 0,
                       'short_run_ticks_without_complete_window': 0,
                       'first_strict_infeasibility_case': None}
              for w in WINDOWS}
    cells = []
    native_replays = 0
    require(len(v3['source_matrix']) == len(NEW_SCHEDULES) == 3,
            'v4g native schedule count drift')
    for source, (schedule, ticks) in zip(v3['source_matrix'], NEW_SCHEDULES):
        require(source['schedule'] == schedule and
                source['source_external_ticks'] == list(ticks),
                'v4g signed native schedule mismatch')
        case, fabric, plans = fixture_fn(ticks=ticks)
        require(dict((p.node_id, p.pe_id) for p in fabric.placement).get('A') == OWNER,
                'v4g source owner changed')
        for mode, (label, enabled, priority) in zip(source['modes'], ARMS):
            require(mode['mode'] == label, 'v4g signed actor mode drift')
            for cap_record, cap in zip(mode['capacities'], CAPACITIES):
                require(cap_record['native_PE_capacity'] == cap,
                        'v4g native cap changed')
                pplan = replace(plans[1], fabric_slots_per_tick=cap)
                native = native_executor(case, fabric, plans[0], pplan,
                                         plans[2], plans[3],
                                         LiveBVPlanV0e(enabled=enabled, priority=priority))
                require(snapshot(native) == cap_record['original_native_sha256'],
                        'v4g frozen native replay mismatches signed original')
                native_replays += 1
                mem = plans[2]
                domains = dict(mem.domain_slots)
                timeline = native['resources']['timeline']
                headroom = [native_headroom(
                    row, global_cap=cap, owner_cap=dict(pplan.pe_slots)[OWNER],
                    owner_memory_cap=dict(mem.pe_slots)[OWNER],
                    total_memory_cap=mem.fabric_slots_per_tick,
                    O_cap=domains['O'], E_cap=domains['E'])['all_free']
                    for row in timeline]
                for policy in POLICIES:
                    for quota in QUOTAS:
                        rows = cap_record['derived_policies'][policy][str(quota)][
                            'rank_audit']['per_tick_fifo_prefix']
                        require(len(rows) == len(timeline) and
                                all(row['tick'] == timeline[i]['tick']
                                    for i, row in enumerate(rows)),
                                'v4g real ACK/native tick alignment broken')
                        cell = {'schedule': schedule, 'mode': label,
                                'native_global_PE_capacity': cap,
                                'derived_policy': policy, 'ACK_quota': quota,
                                'source_run_frontiers': {}}
                        cells.append(cell)
                        for window in WINDOWS:
                            audit = window_audit(rows, headroom, window)
                            cell['source_run_frontiers'][str(window)] = audit
                            rollup = result[str(window)]
                            rollup['source_contexts'] += 1
                            rollup['source_pending_runs'] += audit['pending_runs']
                            for key in ('complete_zero_grant_windows',
                                        'windows_without_any_native_spare',
                                        'unrestricted_minimum_cover_slots',
                                        'unrestricted_minimum_cover_nonspare',
                                        'optimistic_minimum_nonspare',
                                        'optimistic_minimum_nonspare_slots',
                                        'short_run_ticks_without_complete_window'):
                                rollup[key] += audit[key]
                            if audit['strict_spare_only_feasible']:
                                rollup['strict_spare_only_feasible_contexts'] += 1
                                rollup['feasible_strict_minimum_cover_slots'] += (
                                    audit['strict_minimum_cover_slots'])
                            else:
                                rollup['strict_spare_only_infeasible_contexts'] += 1
                                if rollup['first_strict_infeasibility_case'] is None:
                                    rollup['first_strict_infeasibility_case'] = {
                                        'schedule': schedule, 'mode': label,
                                        'native_global_PE_capacity': cap,
                                        'derived_policy': policy, 'ACK_quota': quota,
                                        'window_inclusive_ticks':
                                            audit['first_strict_infeasibility_witness'],
                                    }
    require(native_replays == observed['original_native_replays'] == 18 and
            len(cells) == observed['derived_source_contexts'] == 72 and
            all(result[str(w)]['complete_zero_grant_windows'] ==
                observed['zero_grant_windows'][str(w)] and
                result[str(w)]['windows_without_any_native_spare'] ==
                observed['zero_grant_windows_with_no_native_resource_slot'][str(w)]
                for w in WINDOWS),
            'v4g signed source/v4d resource window conservation failed')
    for value in result.values():
        require(value['source_contexts'] == 72 and
                value['strict_spare_only_feasible_contexts'] +
                value['strict_spare_only_infeasible_contexts'] == 72 and
                (value['strict_spare_only_infeasible_contexts'] > 0) ==
                (value['windows_without_any_native_spare'] > 0) and
                value['optimistic_minimum_nonspare'] <=
                value['unrestricted_minimum_cover_nonspare'],
                'v4g frontier consistency failure')
    return {
        'schema': SCHEMA, 'status': STATUS,
        'signed_v3tuv_sha256': sha256(raw3).hexdigest(),
        'signed_v4abc_sha256': sha256(raw4).hexdigest(),
        'signed_v4def_sha256': sha256(rawprev).hexdigest(),
        'source_original_native_replays': native_replays,
        'source_derived_contexts': len(cells),
        'window_frontiers': result,
        'source_cells': cells,
        'coverage_model': {
            'constraint': 'each complete all-ready zero-grant W-window has one hypothetical coverage tick',
            'strict': 'coverage tick must fit unused native global/owner PE and O/E memory',
            'optimistic': 'a non-spare coverage tick is a lower-bound conflict, not a proven possible preemption',
            'objective_minimum_slots': 'fewest total coverage ticks, tie fewest non-spare ticks',
            'objective_minimum_nonspare': 'fewest non-spare ticks, tie fewest total coverage ticks',
            'actual_ACK_admission': False,
            'preserves_actual_forward_deadlines_if_reserved': None,
            'changes_actual_source_queue_when_hypothetical_ACK_issues': 'NOT_MODELED',
            'all_arrivals_and_lifetimes_beyond_native_horizon': 'NOT_MODELED',
            'spare_does_not_imply_authorization_or_recipient_credit': True,
        },
        'native_v0e_modified': False,
        'reserved_native_ACK_arbiter_implemented': False,
        'universal_native_ACK_deadline_proven': False,
        'actor_learning_implemented': False,
        'next_gate': 'EXPLICIT_VERSIONED_ARBITER_AND_O_E_OWNER_ADMISSION_REQUIRED',
    }
