"""BV v3t-v3v: source-owned FIFO rank in *grants*, not wall-clock ticks.

The finite queue observation can establish which control a real grant pays.
It cannot establish that the next grant will ever arrive.  Post-native source
deliveries are excluded from native-ready accounting, not negative votes.
"""
from __future__ import annotations

from spk_backvalidation_v2.derived_native_fork_v2g import guard
from spk_backvalidation_v2.derived_actor_service_gap_v3q import (
    audit_actor_service_gap,
)

SCHEMA = 'spk-bv-finite-source-actor-grant-rank-certificate/v3t-v3v'


def audit_grant_rank(acks, paid, probes, ledger, summary, receiver,
                     delivered_records, *, policy, global_quota,
                     native_PE_budget):
    """Prove source FIFO-prefix and exact conditional grant-rank accounting.

    In each observed native tick, ACKs must be the prefix of *currently*
    outstanding (due_tick, judgment_id) records. The rank of record J at its
    due tick is the number of real grants needed to reach J if future grants
    keep that prefix property. A censored J has received fewer than rank(J)
    source grants; its eventual service time is never inferred.
    """
    predecessor = audit_actor_service_gap(
        acks, paid, probes, ledger, summary, receiver, delivered_records,
        policy=policy, global_quota=global_quota,
        native_PE_budget=native_PE_budget)
    first_tick, last_tick = probes[0]['tick'], probes[-1]['tick']
    records = {r['identity']: r for r in delivered_records}
    index = {a['judgment_id']: i for i, a in enumerate(acks)}
    guard(len(index) == len(acks), 'v3t duplicate globally paid judgment')
    ack_order = [a['serviced_tick'] for a in acks]
    guard(ack_order == sorted(ack_order),
          'v3t ACK journal not in monotone source service sequence')
    grant_tick_count = 0
    grant_units = 0
    competing_actor_ticks = 0
    prefix_witness = None
    per_tick = []
    for probe in probes:
        tick = probe['tick']
        waiting = sorted(
            (r['due_tick'], r['identity'], r['recipient'])
            for r in delivered_records
            if r['due_tick'] <= tick and
            (r['identity'] not in index or
             acks[index[r['identity']]]['serviced_tick'] >= tick))
        granted = [a for a in acks if a['serviced_tick'] == tick]
        granted_ids = [a['judgment_id'] for a in granted]
        guard(len(granted) == probe['pre_forward_ACK_grants'] and
              granted_ids == [r[1] for r in waiting[:len(granted)]] and
              len(granted) <= global_quota,
              'v3t source grant bypassed older ready judgment or replayed quota')
        if granted:
            grant_tick_count += 1
            grant_units += len(granted)
            if len(waiting) > len(granted):
                competing_actor_ticks += int(bool(
                    {r[2] for r in waiting[len(granted):]} -
                    {a['actor'] for a in granted}))
            if prefix_witness is None and len(waiting) > len(granted):
                prefix_witness = {
                    'tick': tick,
                    'oldest_ready_identity': waiting[0][1],
                    'source_granted_prefix': granted_ids,
                    'still_waiting': [r[1] for r in waiting[len(granted):]],
                }
        per_tick.append({'tick': tick, 'ready_control_count': len(waiting),
                         'grant_prefix_count': len(granted),
                         'oldest_ready_identity': waiting[0][1] if waiting else None})
    guard(grant_units == len(acks) and
          competing_actor_ticks == predecessor[
              'global_grant_with_unserved_actor_ticks'],
          'v3t source per-actor progress/fair FIFO prefix reconciliation failed')
    totals = {
        'source_native_ticks': len(probes),
        'source_grant_ticks': grant_tick_count,
        'source_grant_units': grant_units,
        'eligible_delivered_native_controls': 0,
        'source_serviced_controls': 0,
        'native_horizon_censored_controls': 0,
        'post_native_deliveries_not_native_ready': 0,
        'maximum_due_rank': 0,
        'sum_due_rank_serviced': 0,
        'sum_due_rank_censored': 0,
        'conditional_exact_rank_serviced': 0,
        'conditional_rank_not_reached_censored': 0,
        'global_grant_with_other_actor_waiting_ticks': competing_actor_ticks,
    }
    rank_witnesses = []
    for record in delivered_records:
        due, identity = record['due_tick'], record['identity']
        if due > last_tick:
            totals['post_native_deliveries_not_native_ready'] += 1
            continue
        guard(first_tick <= due <= last_tick,
              'v3t source judgment due outside observed native clock')
        paid_before_due = {a['judgment_id'] for a in acks
                           if a['serviced_tick'] < due}
        due_waiting = sorted((r['due_tick'], r['identity'])
                             for r in delivered_records
                             if r['due_tick'] <= due and
                             r['identity'] not in paid_before_due)
        rank = due_waiting.index((due, identity)) + 1
        totals['eligible_delivered_native_controls'] += 1
        totals['maximum_due_rank'] = max(totals['maximum_due_rank'], rank)
        if identity in index:
            ack_position = index[identity]
            grants_to_service = sum(1 for a in acks[:ack_position+1]
                                    if a['serviced_tick'] >= due)
            guard(grants_to_service == rank,
                  'v3u source ACK rank differs from real post-due grant count')
            totals['source_serviced_controls'] += 1
            totals['conditional_exact_rank_serviced'] += 1
            totals['sum_due_rank_serviced'] += rank
            if len(rank_witnesses) < 3:
                rank_witnesses.append({'actor': record['recipient'],
                    'judgment_id': identity, 'due_tick': due,
                    'due_queue_rank': rank,
                    'real_global_grants_until_service': grants_to_service,
                    'serviced_tick': acks[ack_position]['serviced_tick'],
                    'status': 'SERVED_CONDITIONALLY_EXACT'})
        else:
            grants_to_horizon = sum(1 for a in acks
                                    if a['serviced_tick'] >= due)
            guard(grants_to_horizon < rank,
                  'v3u unserviced actor had enough source global grants for rank')
            totals['native_horizon_censored_controls'] += 1
            totals['conditional_rank_not_reached_censored'] += 1
            totals['sum_due_rank_censored'] += rank
    guard(totals['eligible_delivered_native_controls'] ==
              totals['source_serviced_controls']+
              totals['native_horizon_censored_controls'] and
          totals['native_horizon_censored_controls'] == sum(
              a['unserved_at_native_end_censored']
              for a in predecessor['actor_totals'].values()) and
          totals['post_native_deliveries_not_native_ready'] ==
              receiver['post_native_deliveries'] and
          totals['source_serviced_controls'] == len(acks),
          'v3v source native, post-native, paid rank accounting not conserved')
    return {
        'schema': SCHEMA,
        'totals': totals,
        'per_tick_fifo_prefix': per_tick,
        'first_global_grant_with_unserviced_peer': prefix_witness,
        'exact_grant_rank_witnesses': rank_witnesses,
        'source_FIFO_prefix_for_observed_context': True,
        'source_conditional_grant_rank_verified': True,
        'future_grant_arrival_or_tick_deadline_proven': False,
        'native_actor_fair_scheduler_or_learning_proven': False,
    }
