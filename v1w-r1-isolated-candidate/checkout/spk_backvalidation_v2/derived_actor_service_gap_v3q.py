"""BV v3q-v3s: actor-addressed, source-custodied finite ACK waiting.

The actor's delivered receiver judgments, not aggregate global grants, define
its eligible work.  A deadline is never inferred beyond this finite native
execution.  This checker does not change the frozen scheduler or actor state.
"""
from __future__ import annotations

from collections import Counter

from spk_backvalidation_v2.derived_native_fork_v2g import guard
from spk_backvalidation_v2.derived_ack_wait_gap_v3n import audit_ready_gap

SCHEMA = 'spk-bv-actor-owned-finite-ACK-service-gap/v3q-v3s'
CAUSES = ('native_veto', 'consumer_first', 'peer_granted',
          'ACK_first_resource_unproven')


def audit_actor_service_gap(acks, paid, probes, ledger, summary, receiver,
                            delivered_records, *, policy, global_quota,
                            native_PE_budget):
    """Reconstruct each actor's ready controls from delivered source custody.

    Source delivery occurs on `due_tick` on each native clock step; records
    delivered by the explicit post-native close are kept out of native-ready
    denominators.  Unserved controls at the last native tick are censored.
    """
    global_audit = audit_ready_gap(acks, paid, probes, ledger, summary, receiver,
                                   policy=policy, global_quota=global_quota,
                                   native_PE_budget=native_PE_budget)
    guard(type(delivered_records) is list and
          all(type(row) is dict for row in delivered_records),
          'v3q delivered actor mailbox not a source-owned record list')
    first_tick, last_tick = probes[0]['tick'], probes[-1]['tick']
    record_by_id = {}
    owned = {}
    for record in delivered_records:
        identity, actor, due, created = (
            record.get('identity'), record.get('recipient'),
            record.get('due_tick'), record.get('created_tick'))
        guard(type(identity) is str and bool(identity) and
              identity not in record_by_id and
              type(actor) is str and actor in ('A', 'B', 'C') and
              type(due) is int and type(created) is int and
              0 <= created < due and
              record.get('response') in (-1, 1) and
              type(record.get('issuer')) is str and
              type(record.get('source_emission')) is str and
              bool(record['source_emission']) and
              record['issuer'] != actor,
              'v3q duplicate/forged/early actor mailbox judgment')
        record_by_id[identity] = record
        owned.setdefault(actor, []).append(record)
    guard(len(record_by_id) == receiver['control_delivered'] and
          receiver['post_native_deliveries'] == sum(
              r['due_tick'] > last_tick for r in delivered_records) and
          receiver['delivered_by_sender'] == {
              a: len(rs) for a, rs in sorted(owned.items())},
          'v3q mailbox delivery, native cutoff or actor custody drift')
    ack_by_id, ack_by_tick, ack_by_actor = {}, {}, Counter()
    for ack in acks:
        identity, actor, tick = (ack.get('judgment_id'), ack.get('actor'),
                                 ack.get('serviced_tick'))
        record = record_by_id.get(identity)
        guard(record is not None and identity not in ack_by_id and
              actor == record['recipient'] and
              ack.get('due_tick') == record['due_tick'] and
              ack.get('created_tick') == record['created_tick'] and
              ack.get('response') == record['response'] and
              ack.get('source_emission') == record['source_emission'] and
              ack.get('receiver_issuer') == record['issuer'] and
              type(tick) is int and first_tick <= tick <= last_tick and
              tick >= record['due_tick'] and
              ack.get('resource_phase') == 'native-slack',
              'v3q ACK lacks exact delivered actor custody or native resource')
        ack_by_id[identity] = ack
        ack_by_tick.setdefault(tick, []).append(ack)
        ack_by_actor[actor] += 1
    actors = sorted(set(owned) | set(ack_by_actor))
    actor_totals = {actor: {
        'source_delivered': len(owned.get(actor, [])),
        'post_native_deliveries': 0,
        'native_ready_controls': 0,
        'source_ACKs': ack_by_actor[actor],
        'native_ready_actor_ticks': 0,
        'native_service_actor_ticks': 0,
        'native_missed_actor_ticks': 0,
        'peer_progress_actor_misses': 0,
        'max_consecutive_ready_actor_misses': 0,
        'max_ack_due_to_service_ticks': 0,
        'unserved_at_native_end_censored': 0,
        **{cause+'_miss_ticks': 0 for cause in CAUSES},
    } for actor in actors}
    all_actor_misses = 0
    peer_ticks = 0
    peer_witness = None
    tick_details = []
    streaks = dict.fromkeys(actors, 0)
    for actor in actors:
        rows = owned.get(actor, [])
        actor_totals[actor]['post_native_deliveries'] = sum(
            r['due_tick'] > last_tick for r in rows)
        actor_totals[actor]['native_ready_controls'] = sum(
            r['due_tick'] <= last_tick for r in rows)
        actor_totals[actor]['unserved_at_native_end_censored'] = sum(
            r['due_tick'] <= last_tick and r['identity'] not in ack_by_id
            for r in rows)
    for probe in probes:
        tick, selected = probe['tick'], probe['selected']
        tick_acks = ack_by_tick.get(tick, [])
        serviced = {a['actor'] for a in tick_acks}
        guard(len(serviced) == len(tick_acks) and
              len(tick_acks) == probe['pre_forward_ACK_grants'],
              'v3q per-actor ACK granted twice or disagreeing with source tick')
        waiting = []
        for actor in actors:
            outstanding = [r for r in owned.get(actor, [])
                           if r['due_tick'] <= tick and
                           (r['identity'] not in ack_by_id or
                            ack_by_id[r['identity']]['serviced_tick'] >= tick)]
            if not outstanding:
                streaks[actor] = 0
                guard(actor not in serviced,
                      'v3q source ACK granted absent actor-local ready control')
                continue
            waiting.append(actor)
            totals = actor_totals[actor]
            totals['native_ready_actor_ticks'] += 1
            if actor in serviced:
                totals['native_service_actor_ticks'] += 1
                totals['max_ack_due_to_service_ticks'] = max(
                    totals['max_ack_due_to_service_ticks'],
                    tick-ack_by_tick[tick][next(i for i, a in
                        enumerate(tick_acks) if a['actor'] == actor)]['due_tick'])
                streaks[actor] = 0
                continue
            totals['native_missed_actor_ticks'] += 1
            all_actor_misses += 1
            streaks[actor] += 1
            totals['max_consecutive_ready_actor_misses'] = max(
                totals['max_consecutive_ready_actor_misses'], streaks[actor])
            if probe['native_source_priority_veto']:
                cause = 'native_veto'
            elif selected == 'consumer-first':
                cause = 'consumer_first'
            elif serviced:
                cause = 'peer_granted'
                totals['peer_progress_actor_misses'] += 1
            else:
                cause = 'ACK_first_resource_unproven'
            totals[cause+'_miss_ticks'] += 1
        guard(len(waiting) <= probe['ready_ACKs_before'] and
              serviced.issubset(set(waiting)),
              'v3q actor-local source readiness exceeds original ACK queue')
        peer_missed = sorted(set(waiting)-serviced) if serviced else []
        if peer_missed:
            peer_ticks += 1
            witness = {'tick': tick, 'ready_actors': waiting,
                       'serviced_actors': sorted(serviced),
                       'unserviced_actors': peer_missed}
            if peer_witness is None:
                peer_witness = witness
        tick_details.append({'tick': tick, 'ready_actors': waiting,
                             'serviced_actors': sorted(serviced)})
    guard(sum(x['source_ACKs'] for x in actor_totals.values()) == len(acks) and
          sum(x['native_service_actor_ticks'] for x in actor_totals.values()) ==
              len(acks) and
          all(x['native_ready_actor_ticks'] ==
              x['native_service_actor_ticks']+x['native_missed_actor_ticks'] and
              x['native_missed_actor_ticks'] == sum(x[c+'_miss_ticks']
                                                    for c in CAUSES) and
              x['source_delivered'] == x['post_native_deliveries'] +
              x['source_ACKs'] + x['unserved_at_native_end_censored']
              for x in actor_totals.values()) and
          sum(x['native_missed_actor_ticks'] for x in actor_totals.values()) ==
              all_actor_misses and
          len(tick_details) == len(probes) and
          global_audit['totals']['grant_units'] == len(acks),
          'v3q actor ACK/ready/miss/censoring conservation is not closed')
    return {
        'schema': SCHEMA,
        'actor_totals': actor_totals,
        'actor_ready_misses': all_actor_misses,
        'global_grant_with_unserved_actor_ticks': peer_ticks,
        'first_global_progress_actor_miss_witness': peer_witness,
        'per_tick_actor_readiness': tick_details,
        'source_native_ticks': len(probes),
        'source_ack_count': len(acks),
        'source_delivered': len(delivered_records),
        'source_post_native_delivery_count': receiver['post_native_deliveries'],
        'source_global_gap_max': global_audit['totals'][
            'max_consecutive_ready_miss_ticks'],
        'global_grant_is_not_individual_actor_deadline': True,
        'native_universal_actor_liveness_proven': False,
        'native_learning_proven': False,
    }
