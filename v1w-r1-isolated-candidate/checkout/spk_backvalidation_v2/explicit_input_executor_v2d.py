"""Bounded research executor v2d with explicit external-input timestamps.

Independent micro rules, NOT native CMP or frozen SPK scheduling. Like v2c,
this produces events at actual micro decision/route sites. Simultaneous inputs
remain *separate* admissions; this is a testable micro design choice.
"""
from __future__ import annotations
from dataclasses import dataclass
from heapq import heappop, heappush

from spk_backvalidation_v2.observed_scheduler_v2a import (
    BoundedCaseV2a, ObserverV2a, ObservationV2a, PORT_VERSION, NODES,
    check, validate_case,
)
from spk_backvalidation_v2.time_order_executor_v2c import MAX_TICK

EXECUTOR_VERSION = 'spk-bv-explicit-input-executor/research-v2d'


@dataclass(frozen=True, slots=True)
class ExplicitInputsV2d:
    ticks: tuple[int, ...]
    hop_delay: int = 1


def check_explicit_inputs(case: BoundedCaseV2a, schedule: ExplicitInputsV2d):
    validate_case(case)
    check(type(schedule) is ExplicitInputsV2d and type(schedule.ticks) is tuple and
          len(schedule.ticks) == len(case.stimuli) and
          all(type(t) is int and 1 <= t <= MAX_TICK - 32 for t in schedule.ticks) and
          list(schedule.ticks) == sorted(schedule.ticks) and
          type(schedule.hop_delay) is int and 1 <= schedule.hop_delay <= 8,
          'invalid explicit input schedule')
    return True


def execute_explicit_v2d(case: BoundedCaseV2a, schedule: ExplicitInputsV2d, *,
                         observation_port: ObserverV2a | None = None):
    check_explicit_inputs(case, schedule)
    check(observation_port is None or type(observation_port) is ObserverV2a,
          'invalid observer port')
    if observation_port is not None:
        observation_port._attach()
    heap = [(tick, i, 'A', f'env.{i}') for i, tick in enumerate(schedule.ticks)]
    from heapq import heapify
    heapify(heap)
    serial = len(heap)
    arrivals = {n: 0 for n in NODES}
    emissions = {n: 0 for n in NODES}
    routes = {'A->B': 0, 'B->C': 0}
    emission_ticks = {n: [] for n in NODES}
    decisions = []
    terminal = []
    seen_tokens = set()
    ordinal = 0
    current_tick = 0

    def notify(phase, actor, target, decision_id, parent, token):
        nonlocal ordinal
        if observation_port is not None:
            observation_port._publish(ObservationV2a(
                PORT_VERSION, case.episode, ordinal, current_tick, phase,
                actor, target, decision_id, parent, token))
        ordinal += 1

    try:
        while heap:
            tick, _, actor, parent = heappop(heap)
            check(current_tick <= tick <= MAX_TICK, 'out-of-order or overflow tick')
            current_tick = tick
            ix = NODES.index(actor)
            target = NODES[ix + 1] if ix < 2 else 'TERMINAL'
            if ix:
                check(parent in seen_tokens, 'unowned forwarded token')
                notify('receiver_ingress', actor, NODES[ix-1], '', parent, parent)
            arrivals[actor] += 1
            decision_id = f'{case.episode}.{actor}.d{arrivals[actor]}'
            op = case.operators[ix]
            selected = (op == 'relay' or (op == 'pair' and arrivals[actor] % 2 == 0))
            notify('predecision_expectation', actor, target, decision_id, parent, '')
            notify('decision', actor, target, decision_id, parent, '')
            decisions.append({'node':actor, 'id':decision_id,'operator':op,
                              'selected':selected, 'parent':parent,'tick':tick})
            if not selected:
                continue
            emissions[actor] += 1
            token = f'{case.episode}.{actor}.e{emissions[actor]}'
            check(token not in seen_tokens,'duplicate emission')
            seen_tokens.add(token)
            emission_ticks[actor].append(tick)
            notify('sender_port_emission',actor,target,decision_id,parent,token)
            if target == 'TERMINAL':
                terminal.append(token)
            else:
                routes[f'{actor}->{target}'] += 1
                next_tick = tick + schedule.hop_delay
                check(next_tick <= MAX_TICK - 1, 'forward clock overflow')
                heappush(heap,(next_tick, serial, target, token))
                serial += 1
        current_tick += 1
        check(current_tick <= MAX_TICK, 'invalid final micro tick')
        notify('interval_coverage_close','SCHEDULER','OBSERVER',
               case.episode+'.close','','')
        return {'executor_version':EXECUTOR_VERSION, 'episode':case.episode,
                'input_ticks':list(schedule.ticks), 'hop_delay':schedule.hop_delay,
                'tie_break':'CREATION_SEQUENCE', 'bv_label_only':case.bv_enabled,
                'forward_arrivals':arrivals, 'forward_emissions':emissions,
                'forward_routes':routes,'forward_terminal_count':len(terminal),
                'forward_terminal_tokens':terminal,'emission_ticks':emission_ticks,
                'decisions':decisions,'logical_event_count':ordinal,
                'receiver_B_control_packets':0, 'native_feedback_assessments':0,
                'operator_updates':0}
    finally:
        if observation_port is not None:
            observation_port._detach()
