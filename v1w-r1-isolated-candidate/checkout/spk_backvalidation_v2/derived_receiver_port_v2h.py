"""BV v2h: actor-scoped semantic port in a pinned, in-memory v0e derivative.

Research-only semantics: the receiving actor judges a real admitted spike by
whether its own committed batch emitted anything. Feedback travels in a
separate bounded in-process queue. It does not enter frozen neuronal state,
change the forward scheduler, prove cryptographic identity or update a learner.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from heapq import heappop, heappush
from types import FunctionType
from typing import Callable

from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver, _Instrument, audited_function, guard, EXPECTED_CALLS,
    NativeForkError, PINNED_SCHED,
)

PORT_VERSION = 'spk-bv-derived-actor-semantic-port/research-v2h'
# Anchors are audited *inside* the exact pinned v0e source, not merely by name.
ANCHORS = (('clock', 125), ('ingress', 136), ('batch', 194), ('emission', 217))
MAX_CONTROL = 512


@dataclass(frozen=True, slots=True)
class EmissionV2h:
    identity: str
    sender: str
    receiver: str
    channel: int
    emitted_tick: int
    parents: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class JudgmentV2h:
    identity: str
    issuer: str
    recipient: str
    source_emission: str
    decision: str
    response: int
    created_tick: int
    due_tick: int


class ReceiverPortV2h:
    """Interpreter-local custody; an empty mailbox is NOT negative evidence."""

    def __init__(self, *, feedback=True, capacity=MAX_CONTROL, latency=1,
                 accept: Callable[[JudgmentV2h], bool] | None = None):
        guard(type(feedback) is bool and type(capacity) is int and
              1 <= capacity <= MAX_CONTROL and type(latency) is int and
              1 <= latency <= 16 and (accept is None or callable(accept)),
              'invalid v2h feedback port controls')
        self.feedback, self.capacity, self.latency, self.accept = (
            feedback, capacity, latency, accept)
        self.emissions: dict[str, EmissionV2h] = {}
        self.ingress_ticks: dict[str, int] = {}
        self.judgments: list[JudgmentV2h] = []
        self._decided: set[str] = set()
        self._queued: list[tuple[int, int, JudgmentV2h]] = []
        self._mailboxes: dict[str, list[JudgmentV2h]] = {}
        self._delivered_ids: set[str] = set()
        self._clock = -1
        self._batch_no = 0
        self._sequence = 0
        self.losses = 0
        self.fault_losses = 0
        self.queue_overflow = False
        self.mailbox_overflow = False
        self.post_native_deliveries = 0
        self._closed = False

    def emission(self, occurrence, tick):
        guard(not self._closed and type(occurrence) is dict and type(tick) is int,
              'invalid native emission hook')
        required = ('id', 'source', 'target', 'channel', 'emitted_at', 'parents')
        guard(all(k in occurrence for k in required) and
              type(occurrence['id']) is str and bool(occurrence['id']) and
              type(occurrence['source']) is str and type(occurrence['target']) is str and
              occurrence['source'] != occurrence['target'] and
              type(occurrence['channel']) is int and
              type(occurrence['emitted_at']) is int and occurrence['emitted_at'] == tick and
              type(occurrence['parents']) is tuple and
              all(type(x) is str for x in occurrence['parents']),
              'malformed native emission semantics')
        item = EmissionV2h(occurrence['id'], occurrence['source'],
                           occurrence['target'], occurrence['channel'], tick,
                           occurrence['parents'])
        guard(item.identity not in self.emissions, 'duplicate native emission identity')
        self.emissions[item.identity] = item

    def ingress(self, occurrence, tick):
        guard(not self._closed and type(occurrence) is dict and type(tick) is int,
              'invalid native ingress hook')
        guard(type(occurrence.get('id')) is str,
              'invalid native ingress identity')
        item = self.emissions.get(occurrence.get('id'))
        guard(item is not None and item.receiver == occurrence.get('target') and
              item.sender == occurrence.get('source') and
              item.channel == occurrence.get('channel') and
              item.emitted_tick == occurrence.get('emitted_at') and
              item.parents == occurrence.get('parents') and
              tick > item.emitted_tick and item.identity not in self.ingress_ticks,
              'orphan, altered, early or replayed spike ingress')
        self.ingress_ticks[item.identity] = tick

    def batch(self, actor, tick, items, outputs):
        guard(not self._closed and type(actor) is str and type(tick) is int and
              type(items) is list and type(outputs) in (list, tuple),
              'invalid native receiver decision hook')
        self._batch_no += 1
        decision = f'{actor}.tick{tick}.batch{self._batch_no}'
        # Research criterion: whether the actual actor-local computation
        # produced at least one output; NOT a universal quality/learning law.
        response = 1 if outputs else -1
        for channel, oid in items:
            if oid is None:  # externally injected event, not a BV ancestor
                continue
            origin = self.emissions.get(oid)
            guard(origin is not None and origin.receiver == actor and
                  origin.channel == channel and oid in self.ingress_ticks and
                  self.ingress_ticks[oid] <= tick and oid not in self._decided,
                  'receiver decision lacks admitted source-owned parent')
            self._decided.add(oid)
            record = JudgmentV2h(f'j{len(self.judgments)+1}', actor, origin.sender,
                                 oid, decision, response, tick, tick+self.latency)
            self.judgments.append(record)
            if not self.feedback:
                continue
            if len(self._queued) >= self.capacity:
                self.queue_overflow = True
                continue
            heappush(self._queued, (record.due_tick, self._sequence, record))
            self._sequence += 1

    def _deliver(self, record):
        guard(type(record) is JudgmentV2h and record.identity not in self._delivered_ids,
              'invalid or replayed feedback control')
        origin = self.emissions.get(record.source_emission)
        guard(origin is not None and record.issuer == origin.receiver and
              record.recipient == origin.sender and
              record.created_tick >= self.ingress_ticks.get(origin.identity, 10**9) and
              record.due_tick > record.created_tick and self._clock >= record.due_tick and
              record.response in (-1, 1) and record in self.judgments,
              'forged receiver judgment or causal feedback edge')
        self._delivered_ids.add(record.identity)
        if self.accept is not None:
            try:
                if self.accept(record) is not True:
                    self.losses += 1
                    return 'LOST'
            except Exception:
                self.fault_losses += 1
                return 'FAULT_LOST'
        if sum(map(len, self._mailboxes.values())) >= self.capacity:
            self.mailbox_overflow = True
            return 'OVERFLOW_UNKNOWN'
        self._mailboxes.setdefault(record.recipient, []).append(record)
        return 'DELIVERED'

    def step(self, tick):
        guard(not self._closed and type(tick) is int and tick >= self._clock,
              'nonmonotone v2h control clock')
        self._clock = tick
        while self._queued and self._queued[0][0] <= tick:
            _, _, record = heappop(self._queued)
            self._deliver(record)

    def close(self):
        guard(not self._closed, 'v2h port already closed')
        # Explicitly separate final control-only drain from native ticks.
        while self._queued:
            due = self._queued[0][0]
            before = sum(map(len, self._mailboxes.values()))
            self.step(max(due, self._clock))
            self.post_native_deliveries += sum(map(len, self._mailboxes.values())) - before
        self._closed = True

    def mailbox(self, actor):
        guard(type(actor) is str, 'invalid actor mailbox scope')
        return tuple(self._mailboxes.get(actor, ()))

    def summary(self):
        delivered = [x for box in self._mailboxes.values() for x in box]
        return {
            'port_version': PORT_VERSION,
            'port_closed': self._closed,
            'source_owned_emissions': len(self.emissions),
            'native_ingress_events': len(self.ingress_ticks),
            'receiver_local_judgments': len(self.judgments),
            'positive_judgments': sum(x.response == 1 for x in self.judgments),
            'negative_judgments': sum(x.response == -1 for x in self.judgments),
            'control_delivered': len(delivered),
            'delivered_by_sender': {k:len(v) for k,v in sorted(self._mailboxes.items())},
            'credit_by_sender': {k:sum(x.response for x in v)
                                 for k,v in sorted(self._mailboxes.items())},
            'lost': self.losses, 'fault_lost': self.fault_losses,
            'queue_overflow': self.queue_overflow,
            'mailbox_overflow': self.mailbox_overflow,
            'post_native_deliveries': self.post_native_deliveries,
            'absence_certificates': 0,
            'cryptographic_authentication': False,
            'frozen_actor_state_receives_feedback': False,
            'native_operator_updates': 0,
            'native_learning_proven': False,
        }


def _hook(method, *names):
    return ast.Expr(value=ast.Call(
        func=ast.Attribute(value=ast.Name(id='__v2h_port', ctx=ast.Load()),
                           attr=method, ctx=ast.Load()),
        args=[ast.Name(id=n, ctx=ast.Load()) for n in names], keywords=[]))


class _PortInstrument(ast.NodeTransformer):
    def __init__(self):
        self.found = []

    def visit_While(self, node):
        self.generic_visit(node)
        if node.lineno == 125:
            self.found.append(('clock', node.lineno))
            node.body.insert(0, _hook('step', 'now'))
        return node

    def visit_Expr(self, node):
        self.generic_visit(node)
        if node.lineno == 136:
            self.found.append(('ingress', node.lineno))
            return [node, _hook('ingress', 'item', 'now')]
        if node.lineno == 194:
            self.found.append(('batch', node.lineno))
            return [node, _hook('batch', 'nid', 'now', 'items', 'outs')]
        return node

    def visit_Assign(self, node):
        self.generic_visit(node)
        if node.lineno == 217:
            self.found.append(('emission', node.lineno))
            return [node, _hook('emission', 'occ', 'now')]
        return node


def derive_receiver_executor(source_bytes:bytes, original_executor,
                             port:ReceiverPortV2h, observer:CallsiteObserver):
    """Compile a pinned derived function; frozen module globals stay untouched."""
    guard(type(port) is ReceiverPortV2h and type(observer) is CallsiteObserver and
          isinstance(original_executor, FunctionType) and
          original_executor.__name__ == 'execute_live_v0e',
          'invalid v2h source or instrumentation controls')
    node, callsites = audited_function(source_bytes)
    transformer = _PortInstrument()
    transformed = transformer.visit(node)
    guard(tuple(sorted(transformer.found)) == tuple(sorted(ANCHORS)),
          'v2h audited semantic anchor mismatch')
    callsites_transform = _Instrument()
    transformed = callsites_transform.visit(transformed)
    guard(callsites_transform.count == len(EXPECTED_CALLS),
          'v2h inherited callsite metadata audit mismatch')
    module = ast.Module(body=[ast.ImportFrom(module='__future__',
                 names=[ast.alias(name='annotations')],level=0),transformed],
                 type_ignores=[])
    ast.fix_missing_locations(module)
    isolated = dict(original_executor.__globals__)

    def wrap(name, line, function):
        guard(callable(function), 'noncallable pinned callee')
        def inner(*args, **kwargs):
            try:
                result = function(*args, **kwargs)
            except BaseException:
                observer.emit(name, line, False)
                raise
            observer.emit(name, line, True)
            return result
        return inner

    isolated['__v2h_port'] = port
    isolated['__spk_v2g_wrap'] = wrap
    exec(compile(module, '<spk-v2h-isolated-native-derivative>', 'exec'), isolated)
    derived = isolated['execute_live_v0e']
    guard(derived is not original_executor and
          derived.__code__.co_varnames[:7] == original_executor.__code__.co_varnames[:7],
          'v2h derived native entrypoint contract changed')
    return derived, callsites, tuple(sorted(transformer.found))
