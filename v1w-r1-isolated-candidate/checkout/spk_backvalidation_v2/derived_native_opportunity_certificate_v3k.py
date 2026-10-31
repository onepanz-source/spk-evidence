"""v3k-v3m: falsifiable finite, source-backed ACK opportunity conditions.

No native actor admission, learning or universal native scheduler fairness is
implied. This checker accepts the original queue/resource source observations.
"""
from __future__ import annotations

from collections import Counter

from spk_backvalidation_v2.derived_native_fork_v2g import guard

SCHEMA = 'spk-bv-conditional-source-native-ACK-opportunity-certificate/v3k-v3m'
POLICIES = ('ACK-first', 'bounded-turns')


def audit_native_opportunities(ACKs, paid, probes, ledger, summary, receiver,
                               *, policy, global_quota, native_PE_budget):
    """Audit a *sufficient* local condition, and separately its weak ablation.

    This is strictly a pre-forward source-derived control hypothesis. A tick
    with a ready ACK, no native-ready veto, selected ACK-first and independently
    sufficient unused global/PE/domain resources must charge at least one ACK.
    The same assertion is deliberately NOT made for consumer-first or vetoes.
    """
    guard(type(policy) is str and policy in POLICIES and
          type(global_quota) is int and global_quota in (1, 2) and
          type(native_PE_budget) is int and native_PE_budget in (1, 2) and
          all(type(v) is list for v in (ACKs, paid, probes, ledger)) and
          bool(probes) and len(probes) == len(ledger) and
          type(summary) is dict and type(receiver) is dict and
          summary.get('queue_priority_policy') == policy and
          summary.get('native_operator_updates') == 0 and
          summary.get('frozen_actor_state_changed') is False and
          summary.get('derived_control_tail_grants') == 0 and
          summary.get('derived_actor_credit_ack_count') == len(ACKs) and
          summary.get('concurrent_paid_applications') == len(paid) and
          receiver.get('absence_certificates') == 0 and
          len(paid) <= len(ACKs),
          'v3k opportunity typed source/ACK/consumer/native contract drift')
    delivered = receiver.get('control_delivered')
    other = summary.get('delivered_other_unconsumed_pending')
    blocked = summary.get('delivered_policy_blocked_pending')
    guard(type(delivered) is int and type(other) is int and
          type(blocked) is int and delivered == len(ACKs)+other+blocked and
          other >= 0 and blocked >= 0,
          'v3k source receiver delivered-pending-ACK conservation drift')
    grants = Counter()
    per_actor_tick = Counter()
    epochs = {}
    for ack in ACKs:
        tick, actor, seq = ack.get('serviced_tick'), ack.get('actor'), ack.get('seq')
        guard(type(tick) is int and type(actor) is str and bool(actor) and
              type(seq) is int and seq == epochs.get(actor, 0)+1 and
              ack.get('resource_phase') == 'native-slack' and
              type(ack.get('due_tick')) is int and ack['due_tick'] <= tick,
              'v3k forged source ACK phase, epoch, actor or due tick')
        epochs[actor] = seq
        grants[tick] += 1
        per_actor_tick[(actor, tick)] += 1
    guard(all(n <= global_quota for n in grants.values()) and
          all(n <= 1 for n in per_actor_tick.values()),
          'v3k ACK resource quota or per-actor-once contract drift')
    totals = dict.fromkeys((
        'source_native_ticks', 'ready_native_veto_ticks',
        'ready_nonveto_consumer_first_ticks',
        'ready_nonveto_ACK_first_ticks',
        'weak_no_veto_ready_without_ACK_ticks',
        'sufficient_feasible_ACK_first_ticks',
        'sufficient_feasible_ACK_first_progress_ticks',
        'ACK_first_resource_unproven_ticks',
        'source_inline_ACKs', 'ready_without_grant_streak_max',
    ), 0)
    streak = 0
    for i, (p, row) in enumerate(zip(probes, ledger)):
        tick = p.get('tick')
        ready, observed, selected = (p.get('ready_ACKs_before'),
                                     p.get('pre_forward_ACK_grants'),
                                     p.get('selected'))
        veto = p.get('native_source_priority_veto')
        guard(type(tick) is int and
              tick == probes[0]['tick']+i and
              type(ready) is int and ready >= 0 and
              type(observed) is int and observed >= 0 and
              type(veto) is bool and
              selected in ('native-ready', 'consumer-first', 'ACK-first') and
              row.get('tick') == tick and row.get('phase') == 'native-slack' and
              row.get('service_budget') == native_PE_budget and
              row.get('shadow_control_receipts') == observed == grants[tick] and
              type(row.get('native_service_used')) is int and
              type(row.get('native_memory_used')) is int and
              row.get('shadow_service_units') == observed and
              row.get('shadow_memory_units') == observed*2 and
              type(row.get('memory_budget')) is int and
              type(row.get('pe_service_caps')) is dict and
              type(row.get('pe_memory_caps')) is dict and
              type(row.get('domain_memory_caps')) is dict and
              p.get('ready_forward_before', -1) >= 0 and
              p.get('ready_native_feedback_before', -1) >= 0 and
              veto is bool(p['ready_forward_before'] or
                           p['ready_native_feedback_before']) and
              (not veto or selected == 'native-ready') and
              (selected != 'native-ready' or veto and observed == 0) and
              (selected != 'consumer-first' or not veto and observed == 0) and
              observed <= ready,
              'v3k forged native-ready/ACK-resource tick/counter attribution')
        totals['source_native_ticks'] += 1
        active = ready > 0
        streak = streak+1 if active and not observed else 0
        totals['ready_without_grant_streak_max'] = max(
            totals['ready_without_grant_streak_max'], streak)
        if not active:
            continue
        if veto:
            totals['ready_native_veto_ticks'] += 1
            continue
        if not observed:
            totals['weak_no_veto_ready_without_ACK_ticks'] += 1
        if selected == 'consumer-first':
            totals['ready_nonveto_consumer_first_ticks'] += 1
            continue
        totals['ready_nonveto_ACK_first_ticks'] += 1
        # This strong independent condition is intentionally conservative:
        # zero baseline per-tick PE/memory, a global budget and nonzero
        # *every* admitted owner's PE/memory and O/E domains. If these do not
        # hold, no service theorem is inferred from ready/no-veto alone.
        pe_caps = row['pe_service_caps']
        mem_caps = row['pe_memory_caps']
        domains = row['domain_memory_caps']
        sufficient = (row['native_service_used'] == 0 and
                      row['native_memory_used'] == 0 and
                      native_PE_budget >= 1 and row['memory_budget'] >= 2 and
                      bool(pe_caps) and bool(mem_caps) and
                      all(type(c) is int and c >= 1 for c in pe_caps.values()) and
                      all(type(c) is int and c >= 2 for c in mem_caps.values()) and
                      all(type(domains.get(k)) is int and domains[k] >= 1
                          for k in ('O', 'E')))
        if sufficient:
            totals['sufficient_feasible_ACK_first_ticks'] += 1
            guard(observed >= 1,
                  'v3k source ACK-first resource-feasible native opportunity lost')
            totals['sufficient_feasible_ACK_first_progress_ticks'] += 1
        else:
            totals['ACK_first_resource_unproven_ticks'] += 1
    totals['source_inline_ACKs'] = len(ACKs)
    totals['source_pending_not_negative'] = other+blocked
    totals['real_paid_consumer_receipts'] = len(paid)
    totals['conditional_native_opportunity_witness_not_global_liveness'] = True
    totals['native_learning_or_scheduler_contract_proven'] = False
    totals['schema'] = SCHEMA
    return totals
