"""BV v2v-v2x: source-compiled priority and bounded turns for ACK/consumer.

This is a *derived* source-backed policy discriminator. The v2s consumer
remains independently PE/RAM charged; native forward and BV stay untouched.
Selecting a queue does not grant service unless source budgets actually admit
it; a finite preference window is NOT a universal liveness certificate.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from types import FunctionType

from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver, EXPECTED_CALLS, _Instrument, audited_function, guard,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import (
    ANCHORS, ReceiverPortV2h, _PortInstrument,
)
from spk_backvalidation_v2.derived_actor_priority_v2m import PRE_FORWARD_ANCHOR
from spk_backvalidation_v2.derived_actor_admission_v2k import (
    INLINE_ANCHOR, FINISH_ANCHOR, _IntegratedAdmissionInstrument,
)
from spk_backvalidation_v2.derived_causal_admission_v2o import (
    _NativeCausalPreForwardInstrument, CausalAdmissionPlanV2o,
)
from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import ActorCreditPlanV2l
from spk_backvalidation_v2.derived_actor_control_service_v2j import ShadowServicePlanV2j
from spk_backvalidation_v2.derived_concurrent_consumer_v2s import (
    DerivedConcurrentConsumer, ConcurrentConsumerPlan,
)

SCHEMA = 'spk-bv-derived-actor-ACK-consumer-queue-fairness/research-v2v-v2x'
POLICIES = ('ACK-first', 'consumer-first', 'bounded-turns')


@dataclass(frozen=True, slots=True)
class ActorQueuePlanV2v:
    policy: str = 'bounded-turns'
    max_consecutive_consumer_turns_with_ready_ACK: int = 1


class DerivedActorQueueFairnessV2v(DerivedConcurrentConsumer):
    """Source-owned ready-work veto + two real resource-charged actor queues."""

    def __init__(self, port: ReceiverPortV2h, *,
                 queue_plan: ActorQueuePlanV2v = ActorQueuePlanV2v(),
                 admission_plan: CausalAdmissionPlanV2o = CausalAdmissionPlanV2o(),
                 concurrent_plan: ConcurrentConsumerPlan = ConcurrentConsumerPlan(),
                 credit_plan: ActorCreditPlanV2l = ActorCreditPlanV2l(),
                 service_plan: ShadowServicePlanV2j = ShadowServicePlanV2j()):
        guard(type(queue_plan) is ActorQueuePlanV2v and
              type(queue_plan.policy) is str and queue_plan.policy in POLICIES and
              type(queue_plan.max_consecutive_consumer_turns_with_ready_ACK) is int
              and 0 <= queue_plan.max_consecutive_consumer_turns_with_ready_ACK <= 16,
              'v2v invalid source-bounded ACK/consumer priority policy')
        super().__init__(port, concurrent_plan=concurrent_plan,
                         admission_plan=admission_plan, credit_plan=credit_plan,
                         service_plan=service_plan)
        self.queue_plan = queue_plan
        self._v2v_pre_phase = False
        self._v2v_suppress_ACK = False
        self._v2v_streak = 0
        self._v2v_probes = []

    def _pending(self, tick):
        verified = super()._pending(tick)
        return [] if self._v2v_pre_phase and self._v2v_suppress_ACK else verified

    def _selection(self, backlog, ready_acks, native_veto, streak,
                   consumed_so_far):
        if native_veto:
            return 'native-ready'
        if (not backlog or self.concurrent_plan.max_per_tick == 0 or
                self.concurrent_plan.max_total <= consumed_so_far):
            return 'ACK-first'
        if self.queue_plan.policy == 'ACK-first':
            return 'ACK-first'
        if self.queue_plan.policy == 'consumer-first':
            return 'consumer-first'
        if ready_acks and streak >= (
                self.queue_plan.max_consecutive_consumer_turns_with_ready_ACK):
            return 'ACK-first'
        return 'consumer-first'

    def pre_forward_tick(self, tick, service_used, pe_total, mem_pe_used,
                         mem_dom_used, mem_total, owners, pe_caps, mem_pe_caps,
                         mem_domain_caps, pplan, mplan, pending, outboxes,
                         ready_feedback):
        guard(not self._v2v_pre_phase and not self._v2v_suppress_ACK and
              tick not in {p['tick'] for p in self._v2v_probes} and
              self.port._clock == tick,
              'v2v replayed pre-forward policy or source tick drift')
        # Parent's source-backed mailbox verifier must see the whole mailbox.
        eligible = super()._pending(tick)
        ready_ACKs = len(eligible)
        backlog = len(self._acks) - len(self._v2s_receipts)
        guard(backlog >= 0 and
              all(a.serviced_tick < tick for a in
                  self._acks[len(self._v2s_receipts):]),
              'v2v pre-forward consumer queue contains future ACKs')
        ready_forward = sum(due <= tick and not outboxes[owners[actor]]
                            for due, actor in pending)
        native_feedback = sum(pkt['ready'] <= tick for pkt in ready_feedback)
        native_veto = ((ready_forward > 0 and self.admission_plan.protect_ready_forward)
                       or (native_feedback > 0 and
                           self.admission_plan.protect_ready_native_feedback))
        selected = self._selection(backlog, ready_ACKs, native_veto,
                                   self._v2v_streak, len(self._v2s_receipts))
        previous = self._v2v_streak
        self._v2v_pre_phase = True
        self._v2v_suppress_ACK = selected == 'consumer-first'
        try:
            result = super().pre_forward_tick(
                tick, service_used, pe_total, mem_pe_used, mem_dom_used, mem_total,
                owners, pe_caps, mem_pe_caps, mem_domain_caps, pplan, mplan,
                pending, outboxes, ready_feedback)
        finally:
            self._v2v_pre_phase = False
            self._v2v_suppress_ACK = False
        new_consumer = len(self._v2s_native_pre[tick])
        new_acks = len(self._pre_grants[tick])
        guard(selected != 'native-ready' or not new_consumer and not new_acks,
              'v2v native-ready guard lost PE priority')
        guard(selected != 'consumer-first' or new_acks == 0,
              'v2v consumer-first reservation admitted competing ACK pregrant')
        if selected == 'consumer-first' and ready_ACKs and new_consumer:
            self._v2v_streak = previous + 1
        else:
            self._v2v_streak = 0
        self._v2v_probes.append({
            'tick': tick, 'selected': selected,
            'consumer_backlog_before': backlog,
            'ready_ACKs_before': ready_ACKs,
            'ready_forward_before': ready_forward,
            'ready_native_feedback_before': native_feedback,
            'native_source_priority_veto': native_veto,
            'suppressed_ready_ACKs': ready_ACKs if selected == 'consumer-first' else 0,
            'consumer_pre_forward_charges': new_consumer,
            'pre_forward_ACK_grants': new_acks,
            'consumer_priority_streak_before': previous,
            'consumer_priority_streak_after': self._v2v_streak,
        })
        return result

    def audit_queue_fairness(self):
        super().audit_concurrent()
        guard(self._finished and not self._v2v_pre_phase and
              not self._v2v_suppress_ACK and
              len(self._v2v_probes) == self._original_native_rows and
              [r['tick'] for r in self._v2v_probes] ==
                  list(self._v2s_native_pre),
              'v2v source-authorized arbitration decision trace missing')
        streak = 0
        for item, native in zip(self._v2v_probes, self._admission_probes):
            tick = item['tick']
            backlog = sum(a.serviced_tick < tick for a in self._acks) - sum(
                r.consume_tick < tick for r in self._v2s_receipts)
            previously_consumed = sum(
                r.consume_tick < tick for r in self._v2s_receipts)
            selected = self._selection(item['consumer_backlog_before'],
                item['ready_ACKs_before'], native['native_causal_priority_veto'],
                streak, previously_consumed)
            charges = len(self._v2s_native_pre[tick])
            grants = len(self._pre_grants[tick])
            next_streak = (streak + 1 if selected == 'consumer-first' and
                           item['ready_ACKs_before'] > 0 and charges else 0)
            guard(item['consumer_backlog_before'] == backlog >= 0 and
                  item['consumer_priority_streak_before'] == streak and
                  item['consumer_priority_streak_after'] == next_streak and
                  item['selected'] == selected and
                  item['native_source_priority_veto'] is
                      native['native_causal_priority_veto'] and
                  item['ready_forward_before'] == native[
                      'ready_forward_batches_before_actor_admission'] and
                  item['ready_native_feedback_before'] == native[
                      'ready_native_feedback_packets_before_actor_admission'] and
                  item['consumer_pre_forward_charges'] == charges and
                  item['pre_forward_ACK_grants'] == grants and
                  item['suppressed_ready_ACKs'] == (
                      item['ready_ACKs_before'] if selected == 'consumer-first' else 0) and
                  (selected != 'consumer-first' or grants == 0) and
                  (selected != 'native-ready' or charges == grants == 0) and
                  0 <= item['ready_ACKs_before'] <= 512 and
                  (self.queue_plan.policy != 'bounded-turns' or
                   streak <= self.queue_plan.max_consecutive_consumer_turns_with_ready_ACK),
                  'v2v replay, forged scheduling choice or bounded queue fairness drift')
            streak = next_streak
        guard(streak == self._v2v_streak,
              'v2v per-turn consumer priority counter drift')
        return [dict(x) for x in self._v2v_probes]

    def project_original_native_result(self, derived_result):
        self.audit_queue_fairness()
        return super().project_original_native_result(derived_result)

    def queue_fairness_probes(self):
        return self.audit_queue_fairness()

    def summary(self):
        original = super().summary()
        rows = self.audit_queue_fairness()
        return {**original, 'schema': SCHEMA,
                'queue_priority_policy': self.queue_plan.policy,
                'max_consecutive_consumer_turns_with_ready_ACK':
                    self.queue_plan.max_consecutive_consumer_turns_with_ready_ACK,
                'consumer_first_ticks': sum(r['selected'] == 'consumer-first'
                                            for r in rows),
                'ACK_first_ticks': sum(r['selected'] == 'ACK-first' for r in rows),
                'native_ready_priority_ticks': sum(r['selected'] == 'native-ready'
                                                  for r in rows),
                'ready_ACK_candidates_withheld_pre_forward': sum(
                    r['suppressed_ready_ACKs'] for r in rows),
                'max_observed_competing_consumer_streak': max(
                    r['consumer_priority_streak_after'] for r in rows),
                'universal_ACK_or_consumer_liveness_proven': False,
                'frozen_native_queue_priority_modified': False}


def derive_queue_fairness_executor(source: bytes, original,
                                   port: ReceiverPortV2h,
                                   actor: DerivedActorQueueFairnessV2v,
                                   observer: CallsiteObserver):
    guard(type(port) is ReceiverPortV2h and
          type(actor) is DerivedActorQueueFairnessV2v and actor.port is port and
          type(observer) is CallsiteObserver and isinstance(original, FunctionType) and
          original.__name__ == 'execute_live_v0e',
          'v2v invalid compiled three-way derived queue policy controls')
    node, calls = audited_function(source)
    pre = _NativeCausalPreForwardInstrument()
    transformed = pre.visit(node)
    guard(pre.found == [PRE_FORWARD_ANCHOR], 'v2v source pre-forward anchor drift')
    resource = _IntegratedAdmissionInstrument()
    transformed = resource.visit(transformed)
    guard(resource.inline == [INLINE_ANCHOR] and resource.finish == [FINISH_ANCHOR],
          'v2v PE/RAM resource hooks drift')
    ast.fix_missing_locations(transformed)
    semantic = _PortInstrument()
    transformed = semantic.visit(transformed)
    guard(tuple(sorted(semantic.found)) == tuple(sorted(ANCHORS)),
          'v2v causal receiver-owned source semantic drift')
    callsite = _Instrument()
    transformed = callsite.visit(transformed)
    guard(callsite.count == len(EXPECTED_CALLS),
          'v2v signed frozen callsite inventory changed')
    module = ast.Module(body=[ast.ImportFrom(module='__future__',
        names=[ast.alias(name='annotations')], level=0), transformed], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = dict(original.__globals__)
    native_admit = namespace['_admit']

    def bind_admit(*args, **kwargs):
        result = native_admit(*args, **kwargs)
        guard(type(result) is tuple and len(result) == 2,
              'v2v source original actor ownership changed')
        actor.bind_admitted_actors(*result)
        return result

    def wrap(name, line, fn):
        guard(callable(fn), 'v2v invalid monitored source callsite')
        def run(*args, **kwargs):
            try:
                result = fn(*args, **kwargs)
            except BaseException:
                observer.emit(name, line, False)
                raise
            observer.emit(name, line, True)
            return result
        return run

    namespace['_admit'] = bind_admit
    namespace['__v2h_port'] = port
    namespace['__v2k_admission'] = actor
    namespace['__v2o_causal_admission'] = actor
    namespace['__spk_v2g_wrap'] = wrap
    exec(compile(module, '<spk-v2v-v2x-queue-fairness>', 'exec'), namespace)
    compiled = namespace['execute_live_v0e']
    guard(compiled is not original and
          '__v2k_admission' not in original.__globals__ and
          '__v2o_causal_admission' not in original.__globals__,
          'v2v isolated source clone contaminated frozen native')
    return compiled, calls, tuple(sorted(semantic.found)), (
        PRE_FORWARD_ANCHOR, INLINE_ANCHOR, FINISH_ANCHOR)
