"""BV v2i: bounded actor-batch intake of v2h feedback, in a derived runtime.

The actor batch is real and committed by the pinned scheduler; the inbox,
receipt ledger and credit remain separate research state. No frozen neuron
accepts this feedback, and the credit cannot influence _compute_local.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass

from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver, audited_function, guard,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import (
    ReceiverPortV2h, derive_receiver_executor,
)

SCHEMA = 'spk-bv-derived-actor-batch-control-intake/research-v2i'
MAX_RECEIPTS = 512


@dataclass(frozen=True, slots=True)
class ActorReceiptV2i:
    actor: str
    native_batch_tick: int
    judgment_id: str
    source_emission: str
    issuer: str
    credit_delta: int


class ActorIntakeV2i:
    """Explicit research custody at a committed actor batch, not a learner.

    The adapter may consume only feedback actually delivered by the v2h
    causal port. Quota refusal defers evidence; it never fabricates votes.
    """

    def __init__(self, port: ReceiverPortV2h, *, per_batch=16,
                 max_receipts=MAX_RECEIPTS):
        guard(type(port) is ReceiverPortV2h and type(per_batch) is int and
              1 <= per_batch <= 64 and type(max_receipts) is int and
              1 <= max_receipts <= MAX_RECEIPTS,
              'invalid v2i research intake configuration')
        self.port, self.per_batch, self.max_receipts = (
            port, per_batch, max_receipts)
        self._actors: dict[str, object] = {}
        self._bound = False
        self._last_batch: dict[str, int] = {}
        self._consumed: set[str] = set()
        self._receipts: list[ActorReceiptV2i] = []
        self._batches = 0
        self.receipt_pressure = False
        self.per_batch_pressure = False

    def bind_admitted_actors(self, nodes):
        guard(not self._bound and type(nodes) is dict and bool(nodes) and
              all(type(name) is str and bool(name) and
                  getattr(node, 'node_id', None) == name
                  for name, node in nodes.items()),
              'invalid or duplicated native actor admission')
        self._actors = dict(nodes)
        self._bound = True

    def committed_actor_batch(self, actor, tick):
        guard(self._bound and type(actor) is str and actor in self._actors and
              type(tick) is int and tick >= self._last_batch.get(actor, -1),
              'v2i intake without admitted actor-batch context')
        guard(not self.port._closed, 'v2i intake after control drain')
        self._last_batch[actor] = tick
        self._batches += 1
        due = []
        for record in self.port.mailbox(actor):
            if record.identity in self._consumed:
                continue
            origin = self.port.emissions.get(record.source_emission)
            guard(record.recipient == actor and origin is not None and
                  origin.sender == actor and origin.receiver == record.issuer and
                  record.identity in self.port._delivered_ids and
                  record in self.port.judgments and
                  record.created_tick < record.due_tick <= tick and
                  record.response in (-1, 1),
                  'v2i forged, foreign or premature actor feedback')
            due.append(record)
        if len(due) > self.per_batch:
            self.per_batch_pressure = True
        for record in due[:self.per_batch]:
            if len(self._receipts) >= self.max_receipts:
                self.receipt_pressure = True
                break
            self._consumed.add(record.identity)
            self._receipts.append(ActorReceiptV2i(
                actor, tick, record.identity, record.source_emission,
                record.issuer, record.response))

    def receipts(self, actor):
        guard(type(actor) is str and actor in self._actors,
              'v2i receipt access outside admitted actor')
        return tuple(r for r in self._receipts if r.actor == actor)

    def summary(self):
        guard(self._bound and self.port._closed,
              'v2i summary before native admission or control closure')
        delivered = self.port.summary()['control_delivered']
        guard(len(self._consumed) == len(self._receipts) and
              len(self._receipts) <= delivered,
              'v2i intake ledger accounting mismatch')
        return {
            'schema': SCHEMA,
            'admitted_actors': sorted(self._actors),
            'committed_actor_batch_visits': self._batches,
            'derived_actor_batch_receipts': len(self._receipts),
            'unconsumed_delivered_controls': delivered-len(self._receipts),
            'delivered_controls': delivered,
            'post_native_deliveries_not_native_intake': self.port.post_native_deliveries,
            'delivered_during_native_unconsumed': (
                delivered-len(self._receipts)-self.port.post_native_deliveries),
            'credit_by_actor': {
                actor: sum(r.credit_delta for r in self._receipts if r.actor == actor)
                for actor in sorted(self._actors)},
            'receipts_by_actor': {
                actor: sum(r.actor == actor for r in self._receipts)
                for actor in sorted(self._actors)},
            'receipt_pressure': self.receipt_pressure,
            'per_batch_pressure': self.per_batch_pressure,
            'absence_certificates': 0,
            'frozen_actor_receives_control': False,
            'frozen_state_updates_from_control': 0,
            'operator_learning_updates': 0,
            'native_actor_control_service_resource_accounted': False,
        }


class _PinnedActorBatchProxy:
    """An in-process hook invoked by the actual pinned v2h batch anchor."""

    def __init__(self, port, intake):
        self._port, self._intake = port, intake

    def step(self, tick):
        self._port.step(tick)

    def emission(self, occurrence, tick):
        self._port.emission(occurrence, tick)

    def ingress(self, occurrence, tick):
        self._port.ingress(occurrence, tick)

    def batch(self, actor, tick, items, outputs):
        # The frozen scheduler has already committed this batch at line 194.
        self._port.batch(actor, tick, items, outputs)
        self._intake.committed_actor_batch(actor, tick)


def derive_actor_intake_executor(source: bytes, original, port: ReceiverPortV2h,
                                 intake: ActorIntakeV2i,
                                 observer: CallsiteObserver):
    """Chain the pinned v2h semantic hook with an actor-batch read-only intake.

    The native `_admit` result, not the user-provided fixture, defines the
    actors. The only actor-intake invocation is at the pinned batch hook.
    """
    guard(type(intake) is ActorIntakeV2i and intake.port is port,
          'v2i intake and v2h port must share custody')
    audited, _ = audited_function(source)
    compute_lines = [x.lineno for x in ast.walk(audited)
                     if isinstance(x, ast.Call) and
                     isinstance(x.func, ast.Name) and x.func.id == '_compute_local']
    guard(compute_lines == [183], 'v2i native actor computation anchor drift')
    derived, callsites, anchors = derive_receiver_executor(
        source, original, port, observer)
    namespace = derived.__globals__
    native_admit = namespace['_admit']

    def admit_and_bind(*args, **kwargs):
        result = native_admit(*args, **kwargs)
        guard(type(result) is tuple and len(result) == 2,
              'v2i unexpected native admission result')
        intake.bind_admitted_actors(result[0])
        return result

    namespace['_admit'] = admit_and_bind
    namespace['__v2h_port'] = _PinnedActorBatchProxy(port, intake)
    guard('__v2h_port' not in original.__globals__ and
          '_PinnedActorBatchProxy' not in original.__globals__,
          'v2i adapter leaked into frozen source globals')
    return derived, callsites, anchors
