"""BV v2y–v3a: finite source-owned multi-turn ACK/consumer window witness.

This is a new auditor on the pinned v2v DERIVED actor, not a native scheduler
change. A serviced finite window is an observed safety witness, not a theorem
of starvation freedom, bounded global completion, or native actor learning.
"""
from __future__ import annotations

from dataclasses import dataclass

from spk_backvalidation_v2.derived_native_fork_v2g import guard
from spk_backvalidation_v2.derived_actor_queue_fairness_v2v import (
    ActorQueuePlanV2v, DerivedActorQueueFairnessV2v,
)

SCHEMA = 'spk-bv-source-backed-burst-window-witness/v2y-v3a'


@dataclass(frozen=True, slots=True)
class BurstWindowPressurePlan:
    feedback_latency: int = 2
    ACK_max_per_tick: int = 2
    consumer_max_per_tick: int = 1
    global_PE_slots_per_tick: int = 2
    bounded_consecutive_consumer_turns: int = 1


def validate_burst_pressure(plan: BurstWindowPressurePlan):
    guard(type(plan) is BurstWindowPressurePlan and all(type(x) is int for x in (
        plan.feedback_latency, plan.ACK_max_per_tick, plan.consumer_max_per_tick,
        plan.global_PE_slots_per_tick,
        plan.bounded_consecutive_consumer_turns)) and
        plan == BurstWindowPressurePlan(),
        'v2y source-burst pressure regime changed outside pinned experiment')
    return plan


def audit_burst_window(actor: DerivedActorQueueFairnessV2v,
                       plan: BurstWindowPressurePlan = BurstWindowPressurePlan()):
    """Replay real queue probes and certify finite conditional preference.

    Unlike a liveness certificate, this says only that a queued, source-ready
    ACK is *selected ahead of the consumer* after the measured contention
    streak. Actual ACK service is separately counted, never presumed.
    """
    validate_burst_pressure(plan)
    guard(type(actor) is DerivedActorQueueFairnessV2v and
          type(actor.queue_plan) is ActorQueuePlanV2v and
          actor.queue_plan.max_consecutive_consumer_turns_with_ready_ACK ==
              plan.bounded_consecutive_consumer_turns and
          actor.port.latency == plan.feedback_latency and
          actor.plan.max_per_tick == plan.ACK_max_per_tick and
          actor.concurrent_plan.max_per_tick == plan.consumer_max_per_tick and
          actor._caps is not None and
          actor._caps[3] == plan.global_PE_slots_per_tick,
          'v2y witness actor not in source-bounded real burst regime')
    rows = actor.queue_fairness_probes()
    acks = actor.credit_journal()
    receipts = actor.concurrent_journal()
    guard(len(receipts) <= len(acks) and
          len({r['chain_digest'] for r in receipts}) == len(receipts) and
          len({a['chain_digest'] for a in acks}) == len(acks),
          'v2y duplicate paid consumer or acknowledged source event')
    actual_grants = {}
    for ack in acks:
        tick = ack['serviced_tick']
        actual_grants[tick] = actual_grants.get(tick, 0) + 1
    collisions = 0
    eligible = 0
    forced_ACK_preference = 0
    serviced = 0
    protected_ticks = []
    for row in rows:
        collision = row['consumer_backlog_before'] > 0 and row['ready_ACKs_before'] > 0
        collisions += int(collision)
        activated = (collision and
                     row['consumer_priority_streak_before'] >=
                        plan.bounded_consecutive_consumer_turns and
                     not row['native_source_priority_veto'])
        if activated:
            eligible += 1
            guard(actor.queue_plan.policy != 'bounded-turns' or
                  row['selected'] == 'ACK-first',
                  'v2y violated bounded-turn ACK preference under real contention')
            if actor.queue_plan.policy == 'bounded-turns':
                forced_ACK_preference += 1
                serviced += row['pre_forward_ACK_grants']
                protected_ticks.append(row['tick'])
        guard(row['pre_forward_ACK_grants'] <= actual_grants.get(row['tick'], 0) and
              row['pre_forward_ACK_grants'] <= plan.ACK_max_per_tick and
              row['consumer_pre_forward_charges'] <= plan.consumer_max_per_tick,
              'v2y real ACK/consumer resource charges do not match source ticks')
    return {
        'schema': SCHEMA,
        'policy': actor.queue_plan.policy,
        'source_queue_collision_ticks': collisions,
        'eligible_bounded_turn_windows': eligible,
        'forced_ACK_preference_windows': forced_ACK_preference,
        'ACK_pre_forward_grants_on_forced_windows': serviced,
        'forced_window_source_ticks': protected_ticks,
        'max_competing_consumer_streak': actor.summary()[
            'max_observed_competing_consumer_streak'],
        'ACK_count': len(acks),
        'paid_consumer_count': len(receipts),
        'universal_queue_liveness_proven': False,
        'native_actor_policy_modified': False,
    }
