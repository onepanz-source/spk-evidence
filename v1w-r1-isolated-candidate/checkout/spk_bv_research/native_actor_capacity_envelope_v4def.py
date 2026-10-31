"""BV v4d-v4f: source-pinned native PE/memory *opportunity* envelope.

Replays frozen native executor verbatim, then compares its resource timeline
with derived ACK source FIFO rows. Never schedules a counterfactual ACK or
claims that nominal slack is a live service reservation.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256

from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    LiveBVPlanV0e, execute_live_v0e,
)
from spk_bv_research.native_actor_service_contract_candidate_v4abc import (
    PREDECESSOR_SHA, STATUS as V4_STATUS, analyze_predecessor,
    validate_candidate, validate_signed_v3tuv, source_row_gaps, profiles,
)
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import snapshot
from spk_bv_research.grant_rank_integration_v3tuv import (
    NEW_SCHEDULES, ARMS, CAPACITIES, POLICIES, QUOTAS,
)
from search.spk_bv_v0e_live_evidence import fixture

SCHEMA = 'spk-bv-source-native-reservation-capacity-envelope/research-v4d-v4f'
STATUS = 'SOURCE_REPLAY_RESOURCE_OPPORTUNITY_ONLY_NO_RESERVED_ACK_ADMISSION'
V4_REPORT_SHA = '96b0b33a6ec4fa592459cbe99259b29fa12fe04c182229eb30fed475ce9fbbb3'
WINDOWS = (1, 2, 4, 8)
OWNER = 'PE0'


class EnvelopeRejected(ValueError):
    """Invalid signed evidence or nonconserving resource opportunity."""


def guard(condition, reason):
    if not condition:
        raise EnvelopeRejected(reason)


def native_headroom(tick, *, global_cap, owner_cap, owner_memory_cap,
                    total_memory_cap, O_cap, E_cap, units=1):
    """Can an *additional*, purely abstract owner ACK fit without displacement?

    This reads native occupation; it never reserves, issues or applies an ACK.
    """
    guard(type(tick) is dict and type(units) is int and 1 <= units <= 2 and
          all(type(x) is int and x >= 0 for x in (
              global_cap, owner_cap, owner_memory_cap, total_memory_cap,
              O_cap, E_cap)), 'v4 native opportunity invalid profile')
    pe = tick.get('pe_service_by_pe')
    mem_pe = tick.get('memory_by_pe')
    domains = tick.get('memory_by_domain')
    guard(type(pe) is dict and type(mem_pe) is dict and type(domains) is dict,
          'v4 missing independent owner/memory counters')
    totals = (tick.get('pe_service_total'), tick.get('memory_total'),
              pe.get(OWNER, 0), mem_pe.get(OWNER, 0),
              domains.get('O', 0), domains.get('E', 0))
    guard(all(type(n) is int and n >= 0 for n in totals) and
          totals[0] <= global_cap and totals[2] <= owner_cap and
          totals[1] <= total_memory_cap and
          totals[3] <= owner_memory_cap and
          totals[4] <= O_cap and totals[5] <= E_cap,
          'v4 source native timeline invalid PE/memory budget')
    global_free = totals[0] + units <= global_cap
    owner_free = totals[2] + units <= owner_cap
    memory_free = (totals[1] + 2*units <= total_memory_cap and
                   totals[3] + 2*units <= owner_memory_cap and
                   totals[4] + units <= O_cap and
                   totals[5] + units <= E_cap)
    return {
        'global_PE_free': global_free,
        'owner_PE_free': owner_free,
        'O_E_memory_free': memory_free,
        'all_free': global_free and owner_free and memory_free,
    }


def check_v4_source(v3, raw3, v4, raw4):
    validate_signed_v3tuv(v3, raw3)
    guard(type(v4) is dict and type(raw4) is bytes and
          sha256(raw4).hexdigest() == V4_REPORT_SHA and
          canon(v4) == raw4 and v4.get('status') == V4_STATUS and
          v4.get('signed_predecessor_v3tuv_sha256') == PREDECESSOR_SHA and
          v4.get('native_actor_service_policy_implemented') is False and
          v4.get('native_actor_learning_implemented') is False,
          'v4 capacity audit requires signed, unadmitted v4 proposal')
    exposure = analyze_predecessor(v3, raw3)['source_exposure']
    guard(exposure == v4.get('source_exposure'),
          'v4 source exposure changed across signed evidence')


def evaluate(v3, raw3, v4, raw4, *, fixture_fn=fixture,
             native_executor=execute_live_v0e):
    check_v4_source(v3, raw3, v4, raw4)
    totals = {
        'original_native_replays': 0,
        'min_native_horizon_ticks': None,
        'max_native_horizon_ticks': 0,
        'derived_source_contexts': 0,
        'source_ticks': 0,
        'source_ACK_grants': 0,
        'pending_no_grant_ticks': 0,
        'pending_no_grant_global_PE_full': 0,
        'pending_no_grant_owner_PE_full_after_global_spare': 0,
        'pending_no_grant_memory_full_after_PE_spare': 0,
        'pending_no_grant_all_native_resources_spare': 0,
        'zero_grant_windows': {str(w): 0 for w in WINDOWS},
        'zero_grant_windows_with_no_native_resource_slot': {
            str(w): 0 for w in WINDOWS},
        'zero_grant_windows_with_some_native_resource_slot': {
            str(w): 0 for w in WINDOWS},
        'horizon_rank_shortfall_ticks': {str(w): 0 for w in (4, 8)},
    }
    profiles_examined = []
    horizons_by_capacity = {cap: [] for cap in CAPACITIES}
    guard(len(v3['source_matrix']) == len(NEW_SCHEDULES) and
          len(v3['source_matrix']) == 3,
          'v4 source schedules incomplete')
    for source, (schedule, ticks) in zip(v3['source_matrix'], NEW_SCHEDULES):
        guard(source.get('schedule') == schedule and
              source.get('source_external_ticks') == list(ticks),
              'v4 native schedule identity mismatch')
        case, fabric, plans = fixture_fn(ticks=ticks)
        owner = {p.node_id: p.pe_id for p in fabric.placement}
        guard(owner.get('A') == OWNER and
              tuple(p.node_id for p in case.events) == ('A',)*len(ticks),
              'v4 actor owner mapping drift')
        guard(len(source['modes']) == len(ARMS),
              'v4 native arm count drift')
        for mode, (label, enabled, priority) in zip(source['modes'], ARMS):
            guard(mode.get('mode') == label and
                  len(mode['capacities']) == len(CAPACITIES),
                  'v4 native arm controls drift')
            for cap_record, cap in zip(mode['capacities'], CAPACITIES):
                guard(cap_record.get('native_PE_capacity') == cap,
                      'v4 native global PE resource capacity changed')
                pplan = replace(plans[1], fabric_slots_per_tick=cap)
                result = native_executor(
                    case, fabric, plans[0], pplan, plans[2], plans[3],
                    LiveBVPlanV0e(enabled=enabled, priority=priority))
                guard(snapshot(result) == cap_record['original_native_sha256'],
                      'v4 native replay differs from signed original')
                native_ticks = result['resources']['timeline']
                guard(1 <= len(native_ticks) <= 128 and
                      all(x['tick'] == ticks[0]+i for i, x in enumerate(native_ticks)),
                      'v4 native bounded horizon/clock mismatch')
                totals['original_native_replays'] += 1
                totals['min_native_horizon_ticks'] = min(
                    totals['min_native_horizon_ticks'] or len(native_ticks),
                    len(native_ticks))
                totals['max_native_horizon_ticks'] = max(
                    totals['max_native_horizon_ticks'], len(native_ticks))
                horizons_by_capacity[cap].append(len(native_ticks))
                mem = plans[2]
                owner_cap = dict(pplan.pe_slots)[OWNER]
                owner_mem_cap = dict(mem.pe_slots)[OWNER]
                domains = dict(mem.domain_slots)
                headroom = [native_headroom(
                    t, global_cap=cap, owner_cap=owner_cap,
                    owner_memory_cap=owner_mem_cap,
                    total_memory_cap=mem.fabric_slots_per_tick,
                    O_cap=domains['O'], E_cap=domains['E'])
                    for t in native_ticks]
                for policy in POLICIES:
                    for quota in QUOTAS:
                        sample = cap_record['derived_policies'][policy][str(quota)]
                        rows = sample['rank_audit']['per_tick_fifo_prefix']
                        probe = source_row_gaps(rows)
                        guard(probe['source_ticks'] == len(native_ticks) and
                              all(r['tick'] == native_ticks[i]['tick']
                                  for i, r in enumerate(rows)),
                              'v4 ACK ready/native resource timeline mismatch')
                        cell = {'schedule': schedule, 'mode': label,
                                'native_global_PE_budget': cap,
                                'policy': policy, 'ACK_quota': quota,
                                'source_real_ACK_grants': probe['real_global_ACK_grants'],
                                'pending_no_grant_ticks': 0,
                                'native_spare_pending_no_grant_ticks': 0}
                        totals['derived_source_contexts'] += 1
                        totals['source_ticks'] += len(rows)
                        totals['source_ACK_grants'] += probe['real_global_ACK_grants']
                        for i, r in enumerate(rows):
                            h = headroom[i]
                            grants = r['grant_prefix_count']
                            if grants:
                                guard(native_headroom(
                                    native_ticks[i], global_cap=cap,
                                    owner_cap=owner_cap,
                                    owner_memory_cap=owner_mem_cap,
                                    total_memory_cap=mem.fabric_slots_per_tick,
                                    O_cap=domains['O'], E_cap=domains['E'],
                                    units=grants)['all_free'],
                                    'v4 source ACK grant lacks real native residual budget')
                            if r['ready_control_count'] and not grants:
                                cell['pending_no_grant_ticks'] += 1
                                totals['pending_no_grant_ticks'] += 1
                                if not h['global_PE_free']:
                                    totals['pending_no_grant_global_PE_full'] += 1
                                elif not h['owner_PE_free']:
                                    totals['pending_no_grant_owner_PE_full_after_global_spare'] += 1
                                elif not h['O_E_memory_free']:
                                    totals['pending_no_grant_memory_full_after_PE_spare'] += 1
                                else:
                                    totals['pending_no_grant_all_native_resources_spare'] += 1
                                    cell['native_spare_pending_no_grant_ticks'] += 1
                            if r['ready_control_count']:
                                for w in (4, 8):
                                    # Upper bound on rank that could finish in
                                    # *this finite horizon*, IF the W-premise
                                    # held; no actual slot has been reserved.
                                    slots = (len(rows)-i)//w
                                    if r['ready_control_count'] > slots:
                                        totals['horizon_rank_shortfall_ticks'][str(w)] += 1
                        for w in WINDOWS:
                            name = str(w)
                            for i in range(len(rows)-w+1):
                                block = rows[i:i+w]
                                if (block[0]['ready_control_count'] and
                                    all(r['ready_control_count'] > 0 and
                                        r['grant_prefix_count'] == 0 for r in block)):
                                    totals['zero_grant_windows'][name] += 1
                                    if any(h['all_free'] for h in headroom[i:i+w]):
                                        totals['zero_grant_windows_with_some_native_resource_slot'][name] += 1
                                    else:
                                        totals['zero_grant_windows_with_no_native_resource_slot'][name] += 1
                        profiles_examined.append(cell)
    guard(totals['original_native_replays'] == 18 and
          totals['derived_source_contexts'] == 72 and
          totals['min_native_horizon_ticks'] == 17 and
          totals['max_native_horizon_ticks'] == 45 and
          totals['source_ticks'] == 2560 and
          totals['source_ACK_grants'] == 329 and
          totals['pending_no_grant_ticks'] == 1812 and
          all(totals['zero_grant_windows'][str(w)] == v4['source_exposure'][
              'overlapping_zero_grant_windows'][str(w)] for w in WINDOWS) and
          sum(totals[k] for k in (
              'pending_no_grant_global_PE_full',
              'pending_no_grant_owner_PE_full_after_global_spare',
              'pending_no_grant_memory_full_after_PE_spare',
              'pending_no_grant_all_native_resources_spare')) ==
          totals['pending_no_grant_ticks'] and
          all(totals['zero_grant_windows_with_no_native_resource_slot'][str(w)] +
              totals['zero_grant_windows_with_some_native_resource_slot'][str(w)] ==
              totals['zero_grant_windows'][str(w)] for w in WINDOWS),
          'v4 native-source envelope conservation mismatch')
    cost = []
    for w in (2, 4, 8):
        candidate = {**profiles()['RESERVED_ACK_WINDOW_4'], 'window_ticks': w}
        guard(validate_candidate(candidate)['rate_assumption_proven_by_admission'] is False,
              'v4 candidate unexpectedly admitted')
        for cap in CAPACITIES:
            horizons = horizons_by_capacity[cap]
            cost.append({
                'window_ticks': w, 'global_PE_capacity': cap,
                'minimum_reserved_ACK_grant_units_per_window_if_pending': 1,
                'fully_saturated_global_capacity_share_percent': 100/(w*cap),
                'native_horizon_range_ticks': [min(horizons), max(horizons)],
                'conditional_initial_rank_capacity_range_if_W_premise': [
                    min(horizons)//w, max(horizons)//w],
                'native_replays_with_horizon_at_least_W_times_16':
                    sum(h >= w*16 for h in horizons),
                'requires_native_forward_or_BV_service_reallocation_when_no_slack': True,
                'real_native_reserved_ACK_policy_executed': False,
            })
    return {
        'schema': SCHEMA, 'status': STATUS,
        'signed_v3tuv_sha256': sha256(raw3).hexdigest(),
        'signed_v4abc_sha256': sha256(raw4).hexdigest(),
        'source_native_observed_capacity': totals,
        'source_contexts': profiles_examined,
        'conditional_reservation_envelope': cost,
        'interpretation_limits': [
            'observed PE spare is an upper bound on possible ACK admission, not a grant',
            'overlapping windows are dependent and cannot be summed as service costs',
            'source-ready includes records without all future policy admissions',
            'strictly saturated windows require displacement or new capacity',
            'no forward completion time/energy cost has been simulated',
            'native P/S learning not implemented or inferred',
        ],
        'native_v0e_modified': False,
        'any_reserved_service_contract_implemented': False,
        'any_native_actor_liveness_or_learning_proven': False,
        'next_gate': 'VERSIONED_NATIVE_RESOURCE_ARBITER_REQUIRED_BEFORE_ADOPTION',
    }
