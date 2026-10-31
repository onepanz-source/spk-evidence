"""BV v2s-v2u: an independently paid, causal *pre-forward* actor consumer.

Three cumulative research gates: source-compiled simultaneous scheduling;
independent ACK/consumer PE+RAM custody and pressure discrimination; replay,
negative controls and bounded-horizon refusal. Frozen native remains untouched.

The earlier v2q consumer lane is deliberately disabled, not reused with a
misleading post-forward phase. This class owns a NEW FIFO consumer protocol.
"""
from __future__ import annotations

import ast
from collections import Counter
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
from types import FunctionType

from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver, EXPECTED_CALLS, _Instrument, audited_function, guard,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import (
    ANCHORS, ReceiverPortV2h, _PortInstrument,
)
from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import (
    ZERO_ROOT, ActorCreditPlanV2l,
)
from spk_backvalidation_v2.derived_actor_control_service_v2j import ShadowServicePlanV2j
from spk_backvalidation_v2.derived_actor_admission_v2k import (
    INLINE_ANCHOR, FINISH_ANCHOR, SNAPSHOT_KEYS, _IntegratedAdmissionInstrument,
)
from spk_backvalidation_v2.derived_actor_priority_v2m import PRE_FORWARD_ANCHOR
from spk_backvalidation_v2.derived_causal_admission_v2o import (
    CausalAdmissionPlanV2o, _NativeCausalPreForwardInstrument,
)
from spk_backvalidation_v2.derived_actor_resource_consumer_v2q import (
    ConsumerResourcePlanV2q, DerivedActorResourceConsumerV2q,
    _snap, _budget_tail_row,
)

SCHEMA = 'spk-bv-derived-concurrent-pre-forward-actor-consumer/research-v2s-v2u'
PHASES = ('before-native-forward', 'derived-concurrent-consumer-tail')


@dataclass(frozen=True, slots=True)
class ConcurrentConsumerPlan:
    max_per_tick: int = 1
    max_total: int = 512
    max_tail_ticks: int = 32


@dataclass(frozen=True, slots=True)
class ConcurrentConsumerReceipt:
    actor: str
    owner_pe: str
    consumer_seq: int
    ack_digest: str
    ack_seq: int
    judgment_id: str
    response: int
    ack_service_tick: int
    consume_tick: int
    consume_phase: str
    applied_before: int
    applied_after: int
    pe_service_units: int
    memory_units: int
    chain_prev: str
    chain_digest: str


def _receipt_digest(receipt):
    return sha256(json.dumps(asdict(replace(receipt, chain_digest='')),
            sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()).hexdigest()


class DerivedConcurrentConsumer(DerivedActorResourceConsumerV2q):
    """Actually spends consumer capacity before native work when ACKs are ready.

    Auditably strips *only* these added costs on resource projection. A changed
    native event schedule is never projected away or claimed native parity.
    """

    def __init__(self, port: ReceiverPortV2h, *,
                 concurrent_plan: ConcurrentConsumerPlan = ConcurrentConsumerPlan(),
                 admission_plan: CausalAdmissionPlanV2o = CausalAdmissionPlanV2o(),
                 credit_plan: ActorCreditPlanV2l = ActorCreditPlanV2l(),
                 service_plan: ShadowServicePlanV2j = ShadowServicePlanV2j()):
        guard(type(concurrent_plan) is ConcurrentConsumerPlan and
              all(type(x) is int for x in (concurrent_plan.max_per_tick,
                  concurrent_plan.max_total, concurrent_plan.max_tail_ticks)) and
              0 <= concurrent_plan.max_per_tick <= 16 and
              0 <= concurrent_plan.max_total <= 512 and
              0 <= concurrent_plan.max_tail_ticks <= 128,
              'v2s invalid independent pre-forward consumer capacity policy')
        super().__init__(port, admission_plan=admission_plan,
                         credit_plan=credit_plan, service_plan=service_plan,
                         resource_plan=ConsumerResourcePlanV2q(
                             max_total_consumer_charges=0))
        self.concurrent_plan = concurrent_plan
        self._v2s_receipts = []
        self._v2s_root = ZERO_ROOT
        self._v2s_seq = {}
        self._v2s_credit = {}
        self._v2s_actor_roots = {}
        self._v2s_trace = []
        self._v2s_native_pre = {}
        self._v2s_native_post = {}
        self._v2s_tail = []

    def bind_admitted_actors(self, nodes, owners):
        super().bind_admitted_actors(nodes, owners)
        self._v2s_seq = {actor: 0 for actor in sorted(nodes)}
        self._v2s_credit = {actor: 0 for actor in sorted(nodes)}
        self._v2s_actor_roots = {actor: ZERO_ROOT for actor in sorted(nodes)}

    def _concurrent_service(self, tick, phase, used, pe, mem_pe, dom, memory,
                            caps, *, blocked=False):
        guard(phase in PHASES and type(tick) is int and
              type(blocked) is bool and
              all(type(x) is Counter for x in (used, mem_pe, dom)) and
              type(pe) is int and type(memory) is int,
              'v2s unowned resource/phase input')
        pe_caps, mem_caps, dom_caps, pe_budget, mem_budget = caps
        before = _snap(pe, used, memory, mem_pe, dom)
        start = len(self._v2s_receipts)
        reason = None
        limit = (0 if blocked else min(self.concurrent_plan.max_per_tick,
                    self.concurrent_plan.max_total - start))
        for ack in self._acks[start:]:
            if len(self._v2s_receipts) - start >= limit:
                reason = 'native-priority-veto' if blocked else 'throughput-or-total-bound'
                break
            if ack.serviced_tick > tick:
                reason = 'not-yet-serviced'
                break
            owner, actor = ack.owner_pe, ack.actor
            guard(actor in self._owners and owner == self._owners[actor] and
                  ack.judgment_id in self._acked_ids,
                  'v2s receiver-ACK owner/source custody forged')
            if pe + 1 > pe_budget or used[owner] + 1 > pe_caps[owner]:
                reason = 'independent-PE-pressure'
                break
            if (memory + 2 > mem_budget or mem_pe[owner] + 2 > mem_caps[owner]
                    or dom['O'] + 1 > dom_caps['O'] or dom['E'] + 1 > dom_caps['E']):
                reason = 'independent-memory-pressure'
                break
            prior = self._v2s_credit[actor]
            receipt = ConcurrentConsumerReceipt(
                actor, owner, self._v2s_seq[actor] + 1, ack.chain_digest,
                ack.seq, ack.judgment_id, ack.response, ack.serviced_tick,
                tick, phase, prior, prior + ack.response, 1, 2,
                self._v2s_root, '')
            receipt = replace(receipt, chain_digest=_receipt_digest(receipt))
            self._v2s_receipts.append(receipt)
            self._v2s_seq[actor] = receipt.consumer_seq
            self._v2s_credit[actor] = receipt.applied_after
            self._v2s_actor_roots[actor] = receipt.chain_digest
            self._v2s_root = receipt.chain_digest
            used[owner] += 1
            mem_pe[owner] += 2
            dom['O'] += 1
            dom['E'] += 1
            pe += 1
            memory += 2
        new = tuple(self._v2s_receipts[start:])
        after = _snap(pe, used, memory, mem_pe, dom)
        self._v2s_trace.append({
            'tick': tick, 'phase': phase, 'native_priority_veto': blocked,
            'before': before, 'after': after,
            'receipts': [r.chain_digest for r in new],
            'reject_reason': reason, 'source_PE_caps': dict(sorted(pe_caps.items())),
            'source_memory_caps': dict(sorted(mem_caps.items())),
            'source_domain_caps': dict(sorted(dom_caps.items())),
            'source_PE_budget': pe_budget, 'source_memory_budget': mem_budget,
        })
        return pe, memory, new

    def pre_forward_tick(self, tick, service_used, pe_total, mem_pe_used,
                         mem_dom_used, mem_total, owners, pe_caps, mem_pe_caps,
                         mem_domain_caps, pplan, mplan, pending, outboxes,
                         ready_feedback):
        pe_total, mem_total = super().pre_forward_tick(
            tick, service_used, pe_total, mem_pe_used, mem_dom_used, mem_total,
            owners, pe_caps, mem_pe_caps, mem_domain_caps, pplan, mplan,
            pending, outboxes, ready_feedback)
        caps = (dict(pe_caps), dict(mem_pe_caps), dict(mem_domain_caps),
                pplan.fabric_slots_per_tick, mplan.fabric_slots_per_tick)
        guard(tick not in self._v2s_native_pre and self._caps == caps,
              'v2s replayed pre-forward consumer or source capacity drift')
        veto = self._admission_probes[-1]['native_causal_priority_veto']
        pe_total, mem_total, new = self._concurrent_service(
            tick, 'before-native-forward', service_used, pe_total,
            mem_pe_used, mem_dom_used, mem_total, caps, blocked=veto)
        self._v2s_native_pre[tick] = new
        return pe_total, mem_total

    def admit_tick(self, tick, used, pe, mem_pe, dom, memory, owners,
                   pe_caps, mem_caps, dom_caps, pplan, mplan):
        guard(tick in self._v2s_native_pre and tick not in self._v2s_native_post,
              'v2s after-forward source custody missing pre-forward record')
        early = self._v2s_native_pre[tick]
        for r in early:
            guard(used[r.owner_pe] >= 1 and mem_pe[r.owner_pe] >= 2 and
                  dom['O'] >= 1 and dom['E'] >= 1 and pe >= 1 and memory >= 2,
                  'v2s consumer pre-charge missing from derived native counters')
            used[r.owner_pe] -= 1
            mem_pe[r.owner_pe] -= 2
            dom['O'] -= 1
            dom['E'] -= 1
            pe -= 1
            memory -= 2
            for counter in (used, mem_pe, dom):
                for key in list(counter):
                    if counter[key] == 0:
                        del counter[key]
        # v2q/v2l sees the exact native + ACK resource portion and can audit it
        # unchanged; only after that admission do we restore independent cost.
        pe, memory = super().admit_tick(tick, used, pe, mem_pe, dom, memory,
            owners, pe_caps, mem_caps, dom_caps, pplan, mplan)
        before = _snap(pe, used, memory, mem_pe, dom)
        for r in early:
            used[r.owner_pe] += 1
            mem_pe[r.owner_pe] += 2
            dom['O'] += 1
            dom['E'] += 1
            pe += 1
            memory += 2
        after = _snap(pe, used, memory, mem_pe, dom)
        guard(pe <= pplan.fabric_slots_per_tick and
              memory <= mplan.fabric_slots_per_tick and
              all(used[o] <= c for o, c in pe_caps.items()) and
              all(mem_pe[o] <= c for o, c in mem_caps.items()) and
              all(dom[d] <= c for d, c in dom_caps.items()),
              'v2s paid pre-forward consumer oversubscribed source resources')
        self._v2s_native_post[tick] = {'before': before, 'after': after}
        return pe, memory

    def finish(self, next_native_tick, resource_timeline):
        super().finish(next_native_tick, resource_timeline)
        caps = self._caps
        guard(caps is not None and self._finished and
              len(self._v2s_native_pre) == self._original_native_rows,
              'v2s cannot close unaudited native source horizon')
        last = resource_timeline[-1]['tick']
        for step in range(1, self.concurrent_plan.max_tail_ticks + 1):
            if (len(self._v2s_receipts) == len(self._acks) or
                len(self._v2s_receipts) >= self.concurrent_plan.max_total or
                self.concurrent_plan.max_per_tick == 0):
                break
            used, mem_pe, dom = Counter(), Counter(), Counter()
            self._concurrent_service(last+step, 'derived-concurrent-consumer-tail',
                                     used, 0, mem_pe, dom, 0, caps)
            row = _budget_tail_row(self._v2s_trace[-1])
            self._v2s_tail.append(row)
            # Separate custody copies: a caller mutating the returned result
            # must not silently mutate the audit oracle through aliasing.
            resource_timeline.append(deepcopy(row))

    def audit_concurrent(self):
        # Independently validate every inherited ACK and its legacy disabled
        # consumer lane, then replay the distinct pre-forward receipts.
        super().audit_resource_consumer()
        guard(not self._consume_journal and not self._consumer_resource_charges and
              len(self._v2s_trace) == self._original_native_rows + len(self._v2s_tail) and
              len(self._v2s_native_post) == len(self._v2s_native_pre) ==
                  self._original_native_rows and
              len(self._v2s_receipts) <= len(self._acks) and
              len(self._v2s_receipts) <= self.concurrent_plan.max_total,
              'v2s incomplete independent consumer trace or duplicated receipt')
        caps = self._caps
        seq = {actor: 0 for actor in self._actors}
        credit = {actor: 0 for actor in self._actors}
        roots = {actor: ZERO_ROOT for actor in self._actors}
        root = ZERO_ROOT
        consumed = 0
        last_tick = None
        admission_veto_by_tick = {
            row['tick']: row['native_causal_priority_veto']
            for row in self._admission_probes}
        for row in self._v2s_trace:
            tick, phase = row['tick'], row['phase']
            guard((last_tick is None or tick > last_tick) and
                  row['source_PE_caps'] == dict(sorted(caps[0].items())) and
                  row['source_memory_caps'] == dict(sorted(caps[1].items())) and
                  row['source_domain_caps'] == dict(sorted(caps[2].items())) and
                  row['source_PE_budget'] == caps[3] and
                  row['source_memory_budget'] == caps[4] and
                  phase in PHASES,
                  'v2s consumer native clock/PE/RAM source budget drift')
            last_tick = tick
            before = row['before']
            service = Counter(before['pe_service_by_pe'])
            mem = Counter(before['memory_by_pe'])
            dom = Counter(before['memory_by_domain'])
            pe, memory = before['pe_service_total'], before['memory_total']
            expected = []
            rejection = None
            blocked = (phase == 'before-native-forward' and
                       admission_veto_by_tick[tick])
            guard(row['native_priority_veto'] is blocked,
                  'v2s source-native priority veto was forged')
            limit = (0 if blocked else min(self.concurrent_plan.max_per_tick,
                        self.concurrent_plan.max_total - consumed))
            for ack in self._acks[consumed:]:
                if len(expected) >= limit:
                    # At this tick a later ACK may not yet have been created.
                    if ack.serviced_tick <= tick:
                        rejection = ('native-priority-veto' if blocked else
                                     'throughput-or-total-bound')
                    break
                if ack.serviced_tick > tick:
                    break
                owner = ack.owner_pe
                if pe + 1 > caps[3] or service[owner] + 1 > caps[0][owner]:
                    rejection = 'independent-PE-pressure'
                    break
                if (memory + 2 > caps[4] or mem[owner] + 2 > caps[1][owner]
                        or dom['O'] + 1 > caps[2]['O'] or dom['E'] + 1 > caps[2]['E']):
                    rejection = 'independent-memory-pressure'
                    break
                service[owner] += 1
                mem[owner] += 2
                dom['O'] += 1
                dom['E'] += 1
                pe += 1
                memory += 2
                expected.append(ack)
            recorded = self._v2s_receipts[consumed:consumed + len(expected)]
            guard(row['receipts'] == [r.chain_digest for r in recorded] and
                  row['reject_reason'] == rejection and
                  len(recorded) == len(expected) and
                  row['after'] == _snap(pe, service, memory, mem, dom) and
                  pe <= caps[3] and memory <= caps[4] and
                  all(service[o] <= cap for o, cap in caps[0].items()) and
                  all(mem[o] <= cap for o, cap in caps[1].items()) and
                  all(dom[d] <= cap for d, cap in caps[2].items()),
                  'v2s forged consumer capacity, FIFO, resource or rejection trace')
            if phase == 'before-native-forward':
                pre = self._pre_grants[tick]
                base = _snap(len(pre), Counter(g.owner_pe for g in pre),
                             2*len(pre), Counter({o: 2*n for o,n in
                                 Counter(g.owner_pe for g in pre).items()}),
                             Counter({'O': len(pre), 'E': len(pre)})
                             if pre else Counter())
                guard(tick in self._v2s_native_pre and before == base and
                      self._v2s_native_pre[tick] == tuple(recorded),
                      'v2s consumer was not booked after exact pre-forward ACK charge')
                post = self._v2s_native_post[tick]
                source = self._v2q_native_charge_delta[tick]['after']
                reconstruct_pe = Counter(source['pe_service_by_pe'])
                reconstruct_mem = Counter(source['memory_by_pe'])
                reconstruct_dom = Counter(source['memory_by_domain'])
                for paid in recorded:
                    reconstruct_pe[paid.owner_pe] += 1
                    reconstruct_mem[paid.owner_pe] += 2
                    reconstruct_dom['O'] += 1
                    reconstruct_dom['E'] += 1
                guard(post['before'] == source and
                      post['after'] == _snap(source['pe_service_total'] + len(recorded),
                          reconstruct_pe, source['memory_total'] + 2*len(recorded),
                          reconstruct_mem, reconstruct_dom),
                      'v2s forward/ACK/consumer three-way source accounting drift')
            else:
                guard(before == _snap(0, Counter(), 0, Counter(), Counter()) and
                      row['tick'] > self._v2s_trace[self._original_native_rows-1]['tick'],
                      'v2s consumer tail is not a pure derived-service tick')
            for ack, receipt in zip(expected, recorded):
                actor = ack.actor
                guard(receipt.actor == actor and receipt.owner_pe == ack.owner_pe ==
                      self._owners[actor] and receipt.ack_digest == ack.chain_digest and
                      receipt.ack_seq == ack.seq and
                      receipt.judgment_id == ack.judgment_id and
                      receipt.response == ack.response and
                      receipt.ack_service_tick == ack.serviced_tick and
                      receipt.consume_tick == tick and receipt.consume_phase == phase and
                      receipt.consumer_seq == seq[actor] + 1 and
                      receipt.applied_before == credit[actor] and
                      receipt.applied_after == credit[actor] + ack.response and
                      receipt.pe_service_units == 1 and receipt.memory_units == 2 and
                      receipt.chain_prev == root and
                      receipt.chain_digest == _receipt_digest(receipt),
                      'v2s forged pre-forward receipt, actor, owner, causal ACK or digest')
                root = receipt.chain_digest
                seq[actor] += 1
                credit[actor] = receipt.applied_after
                roots[actor] = receipt.chain_digest
            consumed += len(recorded)
        guard(consumed == len(self._v2s_receipts) and
              seq == self._v2s_seq and credit == self._v2s_credit and
              roots == self._v2s_actor_roots and root == self._v2s_root and
              self._v2s_tail == [
                  _budget_tail_row(row) for row in
                  self._v2s_trace[self._original_native_rows:]],
              'v2s consumer register, exactly-once ledger or chain root drift')
        return True

    def project_original_native_result(self, derived_result):
        self.audit_concurrent()
        guard(type(derived_result) is dict and
              type(derived_result.get('resources')) is dict and
              type(derived_result['resources'].get('timeline')) is list and
              len(derived_result['resources']['timeline']) ==
                  self._original_native_rows + self._synthetic_tail_rows +
                  self._v2q_resource_tail_rows + len(self._v2s_tail),
              'v2s complete resource timeline is missing or truncated')
        projected = deepcopy(derived_result)
        timeline = projected['resources']['timeline']
        if self._v2s_tail:
            guard(timeline[-len(self._v2s_tail):] == self._v2s_tail,
                  'v2s unaccounted consumer-only tail resource mutation')
            del timeline[-len(self._v2s_tail):]
        for row in timeline[:self._original_native_rows]:
            pair = self._v2s_native_post[row['tick']]
            guard(all(row.get(key) == pair['after'][key] for key in SNAPSHOT_KEYS),
                  'v2s integrated PE/RAM source resource result was forged')
            row.update(deepcopy(pair['before']))
        return super().project_original_native_result(projected)

    def concurrent_journal(self):
        self.audit_concurrent()
        return [asdict(r) for r in self._v2s_receipts]

    def concurrent_trace(self):
        self.audit_concurrent()
        return deepcopy(self._v2s_trace)

    def summary(self):
        base = super().summary()
        self.audit_concurrent()
        early = sum(r.consume_phase == 'before-native-forward' for r in self._v2s_receipts)
        return {**base, 'schema': SCHEMA,
                'v2q_post_forward_lane_disabled': True,
                'concurrent_paid_applications': len(self._v2s_receipts),
                'concurrent_before_forward_applications': early,
                'concurrent_tail_applications': len(self._v2s_receipts) - early,
                'concurrent_pending_acks': len(self._acks) - len(self._v2s_receipts),
                'concurrent_consumer_credit': dict(sorted(self._v2s_credit.items())),
                'concurrent_consumer_PE_units': len(self._v2s_receipts),
                'concurrent_consumer_memory_units': 2*len(self._v2s_receipts),
                'concurrent_consumer_tail_rows': len(self._v2s_tail),
                'concurrent_capacity_pressure_ticks': sum(r['reject_reason'] in
                    ('independent-PE-pressure', 'independent-memory-pressure')
                    for r in self._v2s_trace),
                'concurrent_last_chain_digest': self._v2s_root,
                'frozen_native_concurrent_actor_consumer_changed': False}


def derive_concurrent_executor(source: bytes, original, port: ReceiverPortV2h,
                               actor: DerivedConcurrentConsumer,
                               observer: CallsiteObserver):
    guard(type(port) is ReceiverPortV2h and type(actor) is DerivedConcurrentConsumer and
          actor.port is port and type(observer) is CallsiteObserver and
          isinstance(original, FunctionType) and original.__name__ == 'execute_live_v0e',
          'v2s invalid derived concurrent compiler contract')
    node, callsites = audited_function(source)
    priority = _NativeCausalPreForwardInstrument()
    transformed = priority.visit(node)
    guard(priority.found == [PRE_FORWARD_ANCHOR], 'v2s pinned pre-forward AST drift')
    integrated = _IntegratedAdmissionInstrument()
    transformed = integrated.visit(transformed)
    guard(integrated.inline == [INLINE_ANCHOR] and integrated.finish == [FINISH_ANCHOR],
          'v2s pinned source resource/closure anchor drift')
    ast.fix_missing_locations(transformed)
    semantic = _PortInstrument()
    transformed = semantic.visit(transformed)
    guard(tuple(sorted(semantic.found)) == tuple(sorted(ANCHORS)),
          'v2s receiver actor semantic source hook drift')
    instrument = _Instrument()
    transformed = instrument.visit(transformed)
    guard(instrument.count == len(EXPECTED_CALLS), 'v2s audited native callsites drift')
    module = ast.Module(body=[ast.ImportFrom(module='__future__',
        names=[ast.alias(name='annotations')], level=0), transformed], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = dict(original.__globals__)
    native_admit = namespace['_admit']

    def bind_admit(*args, **kwargs):
        result = native_admit(*args, **kwargs)
        guard(type(result) is tuple and len(result) == 2,
              'v2s source native actor ownership result drift')
        actor.bind_admitted_actors(*result)
        return result

    def wrap(name, line, callable_fn):
        guard(callable(callable_fn), 'v2s native observed callsite not callable')
        def inner(*args, **kwargs):
            try:
                result = callable_fn(*args, **kwargs)
            except BaseException:
                observer.emit(name, line, False)
                raise
            observer.emit(name, line, True)
            return result
        return inner

    namespace['_admit'] = bind_admit
    namespace['__v2h_port'] = port
    namespace['__v2k_admission'] = actor
    namespace['__v2o_causal_admission'] = actor
    namespace['__spk_v2g_wrap'] = wrap
    exec(compile(module, '<spk-v2s-v2u-derived-concurrent-consumer>', 'exec'), namespace)
    derived = namespace['execute_live_v0e']
    guard(derived is not original and
          '__v2o_causal_admission' not in original.__globals__ and
          '__v2k_admission' not in original.__globals__,
          'v2s separate compiler modified frozen native function globals')
    return derived, callsites, tuple(sorted(semantic.found)), (
        PRE_FORWARD_ANCHOR, INLINE_ANCHOR, FINISH_ANCHOR)
