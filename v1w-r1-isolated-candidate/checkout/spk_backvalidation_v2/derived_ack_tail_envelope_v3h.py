"""v3h-v3j: finite, paid ACK tail envelope from source-derived journals.

This is an observed, causally bound horizon certificate for selected native
episodes and budgets, not an unconditional ACK deadline or a native scheduler
priority contract.
"""
from __future__ import annotations

from collections import Counter

from spk_backvalidation_v2.derived_native_fork_v2g import guard

SCHEMA = 'spk-bv-source-owned-ACK-tail-capacity-and-FIFO-envelope/v3h-v3j'


def audit_tail_envelope(ACKs, paid, probes, summary, port_summary, *,
                        tail_limit, per_tick_quota):
    """Replay a finite delivered→resource-charged ACK tail accounting."""
    guard(type(tail_limit) is int and 0 <= tail_limit <= 32 and
          type(per_tick_quota) is int and per_tick_quota in (1, 2) and
          type(ACKs) is list and type(paid) is list and type(probes) is list and
          bool(probes) and type(summary) is dict and
          type(port_summary) is dict,
          'v3h typed source tail budget or journal invalid')
    end = probes[-1].get('tick')
    guard(type(end) is int and end > 0 and
          all(type(p) is dict and type(p.get('tick')) is int
              for p in probes) and
          [p['tick'] for p in probes] == list(range(probes[0]['tick'], end+1)) and
          port_summary.get('absence_certificates') == 0 and
          summary.get('native_operator_updates') == 0 and
          summary.get('frozen_actor_state_changed') is False and
          summary.get('derived_actor_credit_ack_count') == len(ACKs) and
          summary.get('concurrent_paid_applications') == len(paid),
          'v3h source-native clock/derived paid receipt witness drift')
    delivered = port_summary.get('control_delivered')
    pending_other = summary.get('delivered_other_unconsumed_pending')
    pending_policy = summary.get('delivered_policy_blocked_pending')
    guard(type(delivered) is int and type(pending_other) is int and
          type(pending_policy) is int and
          delivered >= 0 and pending_other >= 0 and pending_policy >= 0 and
          len(ACKs)+pending_other+pending_policy == delivered and
          len(paid) <= len(ACKs),
          'v3h delivered source controls not conserved by ACK/resource custody')
    pending = pending_other+pending_policy
    phases = {'native-slack', 'post-native-tail'}
    per_tick = Counter()
    per_actor_tick = Counter()
    per_actor_tail = Counter()
    last_actor_seq = {}
    tail_acks = []
    future_due = 0
    for ack in ACKs:
        actor, tick, due = ack.get('actor'), ack.get('serviced_tick'), ack.get('due_tick')
        phase, seq = ack.get('resource_phase'), ack.get('seq')
        guard(type(actor) is str and actor and
              type(tick) is int and type(due) is int and
              type(seq) is int and seq > 0 and due <= tick and
              phase in phases and
              seq == last_actor_seq.get(actor, 0)+1,
              'v3h forged actor ACK epoch, clock, due or resource phase')
        last_actor_seq[actor] = seq
        if phase == 'post-native-tail':
            guard(end < tick <= end+tail_limit,
                  'v3h ACK served outside explicitly bounded derived tail')
            tail_acks.append(ack)
            per_tick[tick] += 1
            per_actor_tick[(actor, tick)] += 1
            per_actor_tail[actor] += 1
            future_due += int(due > end+1)
        else:
            guard(tick <= end,
                  'v3h native-slack ACK mislabelled as a tail charge')
    guard(all(n <= per_tick_quota for n in per_tick.values()) and
          all(n <= 1 for n in per_actor_tick.values()) and
          len(tail_acks) <= tail_limit*per_tick_quota and
          summary.get('derived_control_tail_grants') == len(tail_acks),
          'v3h illegal resource tail throughput/per-actor double charge')
    last_tail = max(per_tick, default=end)
    return {
        'schema': SCHEMA,
        'source_native_last_tick': end,
        'delivered_source_controls': delivered,
        'source_ACK_count': len(ACKs),
        'paid_consumer_receipts': len(paid),
        'delivered_pending_not_negative': pending,
        'delivered_policy_blocked_pending': pending_policy,
        'delivered_other_unconsumed_pending': pending_other,
        'tail_ACKs': len(tail_acks),
        'inline_native_slack_ACKs': len(ACKs)-len(tail_acks),
        'tail_limit_ticks': tail_limit,
        'tail_global_grants_per_tick_cap': per_tick_quota,
        'tail_last_actual_grant_offset_ticks': last_tail-end,
        'tail_distinct_serviced_ticks': len(per_tick),
        'tail_source_actor_counts': dict(sorted(per_actor_tail.items())),
        'tail_due_after_first_tail_tick': future_due,
        'resource_charged_tail_grants_within_cap': True,
        'complete_delivered_control_service': pending == 0,
        'universal_ACK_liveness_or_native_actor_contract_proven': False,
    }
