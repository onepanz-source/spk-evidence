"""Finite ACK wait and paid consumer custody audit, source episodes v3b-v3d.

ACK priority is local; native-ready forward/feedback work is a stronger veto.
Therefore even a one-turn consumer bound CANNOT certify a global ACK deadline.
"""
from __future__ import annotations

from dataclasses import dataclass

from spk_backvalidation_v2.derived_native_fork_v2g import guard
from spk_backvalidation_v2.derived_actor_queue_fairness_v2v import (
    DerivedActorQueueFairnessV2v,
)
from spk_backvalidation_v2.derived_actor_burst_window_v2y import audit_burst_window

SCHEMA = 'spk-bv-receiver-due-to-ACK-source-episode-wait-audit/v3b-v3d'


@dataclass(frozen=True, slots=True)
class EpisodeWaitPlan:
    global_PE_slots_per_tick: int = 2
    feedback_latency_ticks: int = 2
    ACK_max_per_tick: int = 2
    consumer_max_per_tick: int = 1
    max_source_external_events: int = 8


def validate_episode_plan(plan: EpisodeWaitPlan):
    guard(type(plan) is EpisodeWaitPlan and
          all(type(x) is int for x in (
              plan.global_PE_slots_per_tick, plan.feedback_latency_ticks,
              plan.ACK_max_per_tick, plan.consumer_max_per_tick,
              plan.max_source_external_events)) and
          plan == EpisodeWaitPlan(),
          'v3b source workload/budget/wait observation outside pinned scope')
    return plan


def audit_episode_wait(actor: DerivedActorQueueFairnessV2v,
                       plan: EpisodeWaitPlan = EpisodeWaitPlan()):
    """Resource-backed, receiver-due to service wait; no deadline promotion."""
    validate_episode_plan(plan)
    guard(type(actor) is DerivedActorQueueFairnessV2v and
          actor.port.latency == plan.feedback_latency_ticks and
          actor.plan.max_per_tick == plan.ACK_max_per_tick and
          actor.concurrent_plan.max_per_tick == plan.consumer_max_per_tick and
          actor._caps is not None and
          actor._caps[3] == plan.global_PE_slots_per_tick,
          'v3b actor not tied to admitted source service budget')
    burst = audit_burst_window(actor)
    ACKs = actor.credit_journal()
    paid = actor.concurrent_journal()
    return audit_source_acks_and_paid_receipts(
        ACKs, paid, burst, actor.queue_plan.policy)


def audit_source_acks_and_paid_receipts(ACKs, paid, burst, policy):
    """Recheck independently copied, already source-audited derived journals."""
    guard(type(ACKs) is list and type(paid) is list and type(burst) is dict and
          policy in ('ACK-first', 'consumer-first', 'bounded-turns') and
          burst.get('policy') == policy and
          burst.get('ACK_count') == len(ACKs) and
          burst.get('paid_consumer_count') == len(paid) and
          burst.get('universal_queue_liveness_proven') is False and
          burst.get('native_actor_policy_modified') is False,
          'v3b source journals or bounded-window witness mismatch')
    reference = {a['chain_digest']: a for a in ACKs}
    guard(len(reference) == len(ACKs) and
          len({a['judgment_id'] for a in ACKs}) == len(ACKs) and
          len(paid) == len(ACKs) and
          all(a['created_tick'] < a['due_tick'] <= a['serviced_tick']
              for a in ACKs),
          'v3b actual source receiver/ACK chain or overdue record drift')
    for receipt in paid:
        ack = reference.get(receipt['ack_digest'])
        guard(ack is not None and
              receipt['judgment_id'] == ack['judgment_id'] and
              receipt['ack_seq'] == ack['seq'] and
              receipt['owner_pe'] == ack['owner_pe'] and
              receipt['actor'] == ack['actor'] and
              receipt['consume_tick'] >= ack['serviced_tick'],
              'v3b paid consumer was not causally preceded by real source ACK')
    waits = [a['serviced_tick']-a['due_tick'] for a in ACKs]
    paid_waits = [r['consume_tick']-reference[r['ack_digest']]['serviced_tick']
                  for r in paid]
    return {
        'schema': SCHEMA,
        'source_derived_queue_policy': policy,
        'source_ACKs': len(ACKs),
        'independently_paid_consumer_receipts': len(paid),
        'max_ACK_due_to_service_wait_ticks': max(waits, default=0),
        'total_ACK_due_to_service_wait_ticks': sum(waits),
        'ACK_wait_positive_count': sum(x > 0 for x in waits),
        'max_ACK_service_to_consumer_wait_ticks': max(paid_waits, default=0),
        'bounded_turn_source_windows': burst['forced_ACK_preference_windows'],
        'actual_ACK_grants_on_bounded_windows': burst[
            'ACK_pre_forward_grants_on_forced_windows'],
        'max_competing_consumer_streak': burst['max_competing_consumer_streak'],
        'frozen_native_scheduler_modified': False,
        'universal_ACK_service_deadline_proven': False,
    }
