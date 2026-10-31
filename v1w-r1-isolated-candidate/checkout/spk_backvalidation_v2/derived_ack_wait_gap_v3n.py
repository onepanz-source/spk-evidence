"""BV v3n-v3p: exact finite, readiness-conditioned ACK waiting gaps.

This is a derived-source audit, not a native scheduler guarantee.  In
particular an unfinished ready interval at the native horizon is censored;
neither missing ACKs nor receiver silence becomes a negative judgment.
"""
from __future__ import annotations

from spk_backvalidation_v2.derived_native_fork_v2g import guard
from spk_backvalidation_v2.derived_native_opportunity_certificate_v3k import (
    audit_native_opportunities,
)

SCHEMA = 'spk-bv-exact-finite-ready-ACK-gap-partition/v3n-v3p'
THRESHOLDS = (1, 2, 4, 8, 16, 32)
MISS_CLASSES = ('native_veto', 'consumer_first', 'ACK_first_resource_unproven')


def audit_ready_gap(acks, paid, probes, ledger, summary, receiver, *,
                    policy, global_quota, native_PE_budget):
    """Partition every source tick and report *observed* ready/no-grant runs.

    The report counts native ticks, not individual ACK deadlines.  A grant to
    one actor need not service another actor; no per-actor bound is inferred.
    """
    old = audit_native_opportunities(
        acks, paid, probes, ledger, summary, receiver, policy=policy,
        global_quota=global_quota, native_PE_budget=native_PE_budget)
    counts = {'native_ticks': 0, 'not_ready_ticks': 0, 'ready_ticks': 0,
              'ready_grant_ticks': 0, 'ready_miss_ticks': 0,
              'native_veto_miss_ticks': 0, 'consumer_first_miss_ticks': 0,
              'ACK_first_resource_unproven_miss_ticks': 0,
              'grant_units': 0, 'censored_at_native_end': 0,
              'eligibility_change_ended_gaps': 0,
              'granted_after_wait_gaps': 0,
              'max_consecutive_ready_miss_ticks': 0,
              'max_grant_ended_miss_ticks': 0}
    episodes = []
    active = None

    def close(reason, terminal_tick):
        nonlocal active
        if active is not None:
            active['end_reason'] = reason
            active['boundary_tick'] = terminal_tick
            episodes.append(active)
            if reason == 'native_horizon_censored':
                counts['censored_at_native_end'] += 1
            elif reason == 'grant':
                counts['granted_after_wait_gaps'] += 1
                counts['max_grant_ended_miss_ticks'] = max(
                    counts['max_grant_ended_miss_ticks'], active['length'])
            else:
                counts['eligibility_change_ended_gaps'] += 1
            active = None

    for p in probes:
        tick = p['tick']
        ready = p['ready_ACKs_before']
        grants = p['pre_forward_ACK_grants']
        counts['native_ticks'] += 1
        counts['grant_units'] += grants
        if not ready:
            guard(grants == 0, 'v3n source cannot grant absent ready ACK')
            counts['not_ready_ticks'] += 1
            close('eligibility_changed_without_grant', tick)
            continue
        counts['ready_ticks'] += 1
        if grants:
            counts['ready_grant_ticks'] += 1
            close('grant', tick)
            continue
        counts['ready_miss_ticks'] += 1
        if p['native_source_priority_veto']:
            cause = 'native_veto'
        elif p['selected'] == 'consumer-first':
            cause = 'consumer_first'
        else:
            cause = 'ACK_first_resource_unproven'
        guard(cause in MISS_CLASSES,
              'v3n unclassified ready but unserviced ACK tick')
        counts[cause+'_miss_ticks'] += 1
        if active is None:
            active = {'start_tick': tick, 'last_miss_tick': tick,
                      'length': 0, 'miss_classes': dict.fromkeys(MISS_CLASSES, 0)}
        active['last_miss_tick'] = tick
        active['length'] += 1
        active['miss_classes'][cause] += 1
        counts['max_consecutive_ready_miss_ticks'] = max(
            counts['max_consecutive_ready_miss_ticks'], active['length'])
    if active is not None:
        close('native_horizon_censored', probes[-1]['tick'])
    guard(counts['native_ticks'] == len(probes) and
          counts['native_ticks'] == counts['not_ready_ticks'] + counts['ready_ticks'] and
          counts['ready_ticks'] == counts['ready_grant_ticks'] + counts['ready_miss_ticks'] and
          counts['ready_miss_ticks'] == sum(counts[k+'_miss_ticks']
                                           for k in MISS_CLASSES) and
          counts['grant_units'] == len(acks) == old['source_inline_ACKs'] and
          counts['max_consecutive_ready_miss_ticks'] ==
              old['ready_without_grant_streak_max'] and
          counts['native_veto_miss_ticks'] == old['ready_native_veto_ticks'] and
          counts['consumer_first_miss_ticks'] ==
              old['ready_nonveto_consumer_first_ticks'] and
          counts['ACK_first_resource_unproven_miss_ticks'] ==
              old['ACK_first_resource_unproven_ticks'] and
          sum(e['length'] for e in episodes) == counts['ready_miss_ticks'] and
          all(e['length'] == sum(e['miss_classes'].values()) for e in episodes),
          'v3n readiness gap classes do not conserve genuine source ticks')
    counts['miss_thresholds_witnessed'] = {
        str(t): counts['max_consecutive_ready_miss_ticks'] >= t
        for t in THRESHOLDS}
    counts['source_delivered'] = receiver['control_delivered']
    counts['source_pending_not_negative'] = old['source_pending_not_negative']
    return {
        'schema': SCHEMA,
        'totals': counts,
        'miss_episodes': episodes,
        'conditional_progress': old['sufficient_feasible_ACK_first_ticks'],
        'conditional_progress_verified': (
            old['sufficient_feasible_ACK_first_progress_ticks'] ==
            old['sufficient_feasible_ACK_first_ticks']),
        'per_actor_deadline_inferred': False,
        'native_future_opportunity_rate_inferred': False,
        'negative_judgment_or_silence_inferred': False,
    }
