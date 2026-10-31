"""Independent v2c bounded, time-ordered research executor; NOT frozen SPK.

The scheduling rule is explicit: inputs enter A at 1+i*stimulus_gap;
a forwarded token is admitted at emission_tick+hop_delay. Same-tick work
uses creation-sequence FIFO tie breaking. No native timestamp authority.

All events originate inside this executor. BV remains a label; no control
mailbox, independent absence witness, authentication or CMP semantics.
"""
from __future__ import annotations
from dataclasses import dataclass
from heapq import heappop, heappush
from typing import Callable

from spk_backvalidation_v2.observed_scheduler_v2a import (
    BoundedCaseV2a, ObserverV2a, ObservationV2a, PORT_VERSION, NODES,
    validate_case, check,
)

EXECUTOR_VERSION = 'spk-bv-time-order-executor/research-v2c'
MAX_GAP = 8
MAX_DELAY = 8
MAX_TICK = 1024


@dataclass(frozen=True, slots=True)
class TemporalPolicyV2c:
    stimulus_gap: int = 2
    hop_delay: int = 1


def check_policy(policy: TemporalPolicyV2c):
    check(type(policy) is TemporalPolicyV2c and
          type(policy.stimulus_gap) is int and 1 <= policy.stimulus_gap <= MAX_GAP and
          type(policy.hop_delay) is int and 1 <= policy.hop_delay <= MAX_DELAY,
          'unsupported temporal policy')
    return True


def execute_time_order_v2c(case: BoundedCaseV2a, *,
                           policy: TemporalPolicyV2c = TemporalPolicyV2c(),
                           observation_port: ObserverV2a | None = None):
    """Event-driven finite micro-runtime; no posthoc producer-count seeding."""
    validate_case(case)
    check_policy(policy)
    check(observation_port is None or type(observation_port) is ObserverV2a,
          'invalid research observer')
    if observation_port is not None:
        observation_port._attach()
    heap = []
    serial = 0
    for i, _ in enumerate(case.stimuli):
        tick = 1 + i * policy.stimulus_gap
        heappush(heap, (tick, serial, 'A', f'env.{i}'))
        serial += 1
    arrivals = {n: 0 for n in NODES}
    emissions = {n: 0 for n in NODES}
    routes = {'A->B': 0, 'B->C': 0}
    emission_ticks = {n: [] for n in NODES}
    arrival_ticks = {n: [] for n in NODES}
    decision_log = []
    seen_tokens = set()
    terminal_tokens = []
    ordinal = 0
    current_tick = 0

    def notify(phase, actor, target, decision_id, parent_token, event_token):
        nonlocal ordinal
        if observation_port is not None:
            observation_port._publish(ObservationV2a(
                PORT_VERSION, case.episode, ordinal, current_tick,
                phase, actor, target, decision_id, parent_token, event_token))
        ordinal += 1

    try:
        while heap:
            tick, seq, actor, parent = heappop(heap)
            check(type(tick) is int and 1 <= tick <= MAX_TICK and tick >= current_tick,
                  'nonmonotone or out-of-bounds research clock')
            current_tick = tick
            i = NODES.index(actor)
            target = NODES[i + 1] if i < 2 else 'TERMINAL'
            # An ingress exists only on actual removal from the event queue.
            if i > 0:
                check(parent in seen_tokens, 'orphaned arrival')
                notify('receiver_ingress', actor, NODES[i-1], '', parent, parent)
            arrivals[actor] += 1
            arrival_ticks[actor].append(tick)
            decision_id = f'{case.episode}.{actor}.d{arrivals[actor]}'
            op = case.operators[i]
            selected = (op == 'relay' or (op == 'pair' and arrivals[actor] % 2 == 0))
            # This local expectation is not a predecision source commitment.
            notify('predecision_expectation', actor, target, decision_id, parent, '')
            notify('decision', actor, target, decision_id, parent, '')
            decision_log.append({'node': actor, 'decision_id': decision_id,
                                 'parent': parent, 'operator': op,
                                 'selected': selected, 'tick': tick})
            if not selected:
                continue
            emissions[actor] += 1
            token = f'{case.episode}.{actor}.e{emissions[actor]}'
            check(token not in seen_tokens, 'reused emission token')
            seen_tokens.add(token)
            emission_ticks[actor].append(tick)
            notify('sender_port_emission', actor, target, decision_id, parent, token)
            if target == 'TERMINAL':
                terminal_tokens.append(token)
            else:
                routes[f'{actor}->{target}'] += 1
                forward_tick = tick + policy.hop_delay
                check(forward_tick <= MAX_TICK, 'forward time outside bounded clock')
                heappush(heap, (forward_tick, serial, target, token))
                serial += 1
        current_tick += 1
        check(current_tick <= MAX_TICK, 'close outside bounded clock')
        notify('interval_coverage_close', 'SCHEDULER', 'OBSERVER',
               f'{case.episode}.close', '', '')
        return {
            'executor_version': EXECUTOR_VERSION, 'episode': case.episode,
            'bv_label_only': case.bv_enabled,
            'policy': {'stimulus_gap': policy.stimulus_gap, 'hop_delay': policy.hop_delay,
                       'tie_break': 'CREATION_SEQUENCE'},
            'forward_arrivals': arrivals, 'forward_emissions': emissions,
            'forward_routes': routes, 'forward_terminal_count': len(terminal_tokens),
            'forward_terminal_tokens': terminal_tokens,
            'forward_decisions': len(decision_log), 'decisions': decision_log,
            'emission_ticks': emission_ticks, 'arrival_ticks': arrival_ticks,
            'logical_event_count': ordinal, 'last_logical_tick': current_tick,
            'receiver_B_control_packets': 0, 'native_feedback_assessments': 0,
            'operator_updates': 0,
        }
    finally:
        if observation_port is not None:
            observation_port._detach()
