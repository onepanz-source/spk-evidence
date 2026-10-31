"""Versioned, EXECUTABLE bounded research scheduler with producer callsites.

This is an independently defined micro-runtime, not a port/copy of frozen
execute_live_v0e or of the full SPK algebra/scheduler. 'relay', 'pair' and
'block' are explicit NEW micro-operators, NOT aliases for frozen CMP.

An observer sees immutable source-created events *before return*; it cannot
change execution, authenticate a neuron, certify silence, or deliver feedback.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable

PORT_VERSION = 'spk-bv-observation-port/research-v2a'
EXECUTOR_VERSION = 'spk-bv-bounded-executor/research-v2a'
MAX_INPUT = 16
MAX_OBSERVATIONS = 512
NODES = ('A', 'B', 'C')
OPERATORS = ('relay', 'pair', 'block')
PHASES = ('predecision_expectation', 'decision', 'sender_port_emission',
          'receiver_ingress', 'interval_coverage_close')


class V2aBoundaryError(ValueError):
    pass


def check(ok: bool, reason: str):
    if not ok:
        raise V2aBoundaryError(reason)


@dataclass(frozen=True, slots=True)
class BoundedCaseV2a:
    """Independent bounded forward experiment; not a frozen-SPK CaseV0e."""
    episode: str
    stimuli: tuple[int, ...]
    operators: tuple[str, str, str]
    bv_enabled: bool = False  # label only; no BV engine implemented in this subset


@dataclass(frozen=True, slots=True)
class ObservationV2a:
    version: str
    episode: str
    ordinal: int
    logical_tick: int
    phase: str
    actor: str
    target: str
    decision_id: str
    parent_token: str
    event_token: str


class ObserverV2a:
    """Best-effort, fail-closed telemetry. Sink never affects the forward run.

    An overflow permanently marks the collection incomplete. Python-local
    object references are NOT cryptographic identity or delivery to B.
    """
    def __init__(self, sink: Callable[[ObservationV2a], None] | None = None,
                 capacity: int = MAX_OBSERVATIONS):
        check(sink is None or callable(sink), 'bad observer sink')
        check(type(capacity) is int and 1 <= capacity <= MAX_OBSERVATIONS,
              'bad observer capacity')
        self.sink = sink
        self.capacity = capacity
        self.events: list[ObservationV2a] = []
        self.overflow = False
        self.sink_fault = False
        self._published = 0
        self._attached = False

    def _attach(self):
        check(not self._attached, 'observer already attached')
        check(not self.events and not self.overflow and not self.sink_fault and
              self._published == 0, 'observer reuse refused')
        self._attached = True

    def _publish(self, record: ObservationV2a):
        check(self._attached and type(record) is ObservationV2a,
              'not an active executor record')
        self._published += 1
        if len(self.events) >= self.capacity:
            self.overflow = True
            return
        self.events.append(record)
        if self.sink is not None and not self.sink_fault:
            try:
                self.sink(record)
            except Exception:
                self.sink_fault = True

    def _detach(self):
        self._attached = False

    def summary(self):
        return {
            'port_version': PORT_VERSION,
            'records_retained': len(self.events),
            'events_offered': self._published,
            'overflow': self.overflow,
            'sink_fault': self.sink_fault,
            'complete': not self.overflow and not self.sink_fault,
            'native_receiver_B_control_messages': 0,
            'independent_absence_certificates': 0,
            'authentication_verified': False,
        }


def validate_case(case: BoundedCaseV2a):
    check(type(case) is BoundedCaseV2a, 'bad bounded case')
    check(type(case.episode) is str and 1 <= len(case.episode) <= 72 and
          all(c.isascii() and (c.isalnum() or c in '._-') for c in case.episode),
          'unsafe episode')
    check(type(case.stimuli) is tuple and 1 <= len(case.stimuli) <= MAX_INPUT and
          all(type(i) is int and i == 1 for i in case.stimuli),
          'unsupported stimuli')
    check(type(case.operators) is tuple and len(case.operators) == 3 and
          all(type(s) is str and s in OPERATORS for s in case.operators),
          'unsupported micro-operator')
    check(type(case.bv_enabled) is bool, 'bad non-operative BV label')
    return True


def execute_live_v2a(case: BoundedCaseV2a, *, observation_port: ObserverV2a | None = None):
    """A genuine in-execution event producer for THIS subset only.

    Actual local decisions, route admission and terminal emission are made
    here, not reconstructed from frozen-v0e post-return counts. No observer
    data enters the calculation or a recipient-local BV judgment.
    """
    validate_case(case)
    check(observation_port is None or type(observation_port) is ObserverV2a,
          'unsupported observation port')
    if observation_port is not None:
        observation_port._attach()

    # All computation state below is local to the executor, not the observer.
    queue = deque((('A', f'env.{i}') for i in range(len(case.stimuli))))
    arrivals = {k: 0 for k in NODES}
    emissions = {k: 0 for k in NODES}
    routes = {'A->B': 0, 'B->C': 0}
    decisions = 0
    logical_tick = 0
    ordinal = 0
    decision_log: list[dict] = []
    terminal_tokens: list[str] = []
    def notify(phase: str, actor: str, target: str,
               decision_id: str, parent_token: str, event_token: str):
        nonlocal logical_tick, ordinal
        logical_tick += 1
        if observation_port is not None:
            # Immutable record produced at the actual event site. Even a
            # faulty callback never becomes a computation or admission gate.
            ev = ObservationV2a(PORT_VERSION, case.episode, ordinal,
                                logical_tick, phase, actor, target,
                                decision_id, parent_token, event_token)
            observation_port._publish(ev)
        ordinal += 1
    try:
        while queue:
            actor, parent = queue.popleft()
            ix = NODES.index(actor)
            target = NODES[ix + 1] if ix < 2 else 'TERMINAL'
            arrivals[actor] += 1
            decisions += 1
            decision_id = f'{case.episode}.{actor}.d{arrivals[actor]}'
            notify('predecision_expectation', actor, target, decision_id, parent, '')
            op = case.operators[ix]
            # These explicitly declared research rules are not CMP opcodes.
            selected = op == 'relay' or (op == 'pair' and arrivals[actor] % 2 == 0)
            notify('decision', actor, target, decision_id, parent, '')
            decision_log.append({'node': actor, 'decision_id': decision_id,
                                 'parent': parent, 'operator': op,
                                 'selected': selected})
            if not selected:
                continue
            emissions[actor] += 1
            token = f'{case.episode}.{actor}.e{emissions[actor]}'
            notify('sender_port_emission', actor, target, decision_id, parent, token)
            if target == 'TERMINAL':
                terminal_tokens.append(token)
            else:
                routes[f'{actor}->{target}'] += 1
                # Receiver arrival really happens as the bounded FIFO runs.
                notify('receiver_ingress', target, actor, decision_id, token, token)
                queue.append((target, token))
        # Logical closure only. NOT an independent clock or absence proof.
        notify('interval_coverage_close', 'SCHEDULER', 'OBSERVER',
               f'{case.episode}.close', '', '')
        return {
            'executor_version': EXECUTOR_VERSION, 'episode': case.episode,
            'bv_label_only': case.bv_enabled,
            'forward_arrivals': arrivals, 'forward_emissions': emissions,
            'forward_routes': routes, 'forward_terminal_count': len(terminal_tokens),
            'forward_terminal_tokens': terminal_tokens,
            'forward_decisions': decisions, 'decisions': decision_log,
            'logical_event_count': ordinal,
            'receiver_B_control_packets': 0,
            'native_feedback_assessments': 0, 'operator_updates': 0,
        }
    finally:
        if observation_port is not None:
            observation_port._detach()
