"""BV v2n: bounded forward opportunity amid derived pre-forward actor credit.

Only the separately recompiled, source-pinned derived scheduler is affected.
The protected opportunity is deliberately NOT a universal liveness theorem:
atomic forward memory, per-PE pressure and an external bounded horizon can
still prevent a ready forward batch from committing.
"""
from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass
from types import FunctionType

from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver,EXPECTED_CALLS,_Instrument,audited_function,guard,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import (
    ANCHORS,ReceiverPortV2h,_PortInstrument,
)
from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import ActorCreditPlanV2l
from spk_backvalidation_v2.derived_actor_control_service_v2j import ShadowServicePlanV2j
from spk_backvalidation_v2.derived_actor_admission_v2k import (
    _IntegratedAdmissionInstrument,INLINE_ANCHOR,FINISH_ANCHOR,
)
from spk_backvalidation_v2.derived_actor_priority_v2m import (
    DerivedActorPriorityV2m,_PreForwardInstrument,PRE_FORWARD_ANCHOR,
)

FAIRNESS_SCHEMA='spk-bv-derived-forward-opportunity-fairness/research-v2n'


@dataclass(frozen=True,slots=True)
class FairnessPlanV2n:
    max_consecutive_actor_ticks_with_ready_forward: int = 1
    protected_forward_pe_slots: int = 1


class DerivedActorFairnessV2n(DerivedActorPriorityV2m):
    """Source-tick forward reservation; no preemption within an atomic batch."""

    def __init__(self,port:ReceiverPortV2h,*,
                 fairness_plan:FairnessPlanV2n=FairnessPlanV2n(),
                 credit_plan:ActorCreditPlanV2l=ActorCreditPlanV2l(),
                 service_plan:ShadowServicePlanV2j=ShadowServicePlanV2j()):
        guard(type(fairness_plan) is FairnessPlanV2n and
              type(fairness_plan.max_consecutive_actor_ticks_with_ready_forward) is int and
              0<=fairness_plan.max_consecutive_actor_ticks_with_ready_forward<=16 and
              type(fairness_plan.protected_forward_pe_slots) is int and
              1<=fairness_plan.protected_forward_pe_slots<=16,
              'v2n invalid finite forward fairness window or reservation')
        super().__init__(port,priority='actor-first',credit_plan=credit_plan,
                         service_plan=service_plan)
        self.fairness_plan=fairness_plan
        self._fair_streak=0
        self._pre_allowance=None
        self._fair_probes=[]
        self._fair_progress=[]

    def _pending(self,tick):
        eligible=super()._pending(tick)  # ALWAYS validate entire causal mailbox
        if self._pre_allowance is not None:
            return eligible[:self._pre_allowance]
        return eligible

    def pre_forward_tick(self,tick,service_used,pe_total,mem_pe_used,
                         mem_dom_used,mem_total,owners,pe_caps,mem_pe_caps,
                         mem_domain_caps,pplan,mplan,pending,outboxes):
        guard(self._pre_allowance is None and
              self.fairness_plan.protected_forward_pe_slots<=pplan.fabric_slots_per_tick,
              'v2n protected forward opportunity outside actual PE capacity')
        ready=sorted((due,actor) for due,actor in pending
                     if due<=tick and not outboxes[owners[actor]])
        prior=self._fair_streak
        max_actor=self.fairness_plan.max_consecutive_actor_ticks_with_ready_forward
        protect=bool(ready) and prior>=max_actor
        # Reservation remains in native-derived counters: inherited v2m
        # _service_tick sees no candidates beyond this causal, FIFO prefix.
        allowance=(max(0,pplan.fabric_slots_per_tick-
                       self.fairness_plan.protected_forward_pe_slots)
                   if protect else self.plan.max_per_tick)
        self._pre_allowance=allowance
        try:
            result=super().pre_forward_tick(tick,service_used,pe_total,
                mem_pe_used,mem_dom_used,mem_total,owners,pe_caps,
                mem_pe_caps,mem_domain_caps,pplan,mplan,pending,outboxes)
        finally:
            self._pre_allowance=None
        actual=len(self._pre_grants[tick])
        guard(actual<=allowance and
              (not protect or result[0]<=pplan.fabric_slots_per_tick-
               self.fairness_plan.protected_forward_pe_slots),
              'v2n actor grants consumed reserved forward opportunity')
        if not ready or protect or not actual:
            self._fair_streak=0
        elif actual:
            self._fair_streak=prior+1
        self._fair_probes.append({
            'tick':tick,'ready_forward_batches':len(ready),
            'actor_streak_before':prior,'actor_streak_after':self._fair_streak,
            'protected_forward_opportunity':protect,
            'reserved_forward_pe_slots':(
                self.fairness_plan.protected_forward_pe_slots if protect else 0),
            'control_pregrant_allowance':allowance,
            'actor_pregrants':actual,
        })
        return result

    def finish(self,next_native_tick,resource_timeline):
        guard(len(self._fair_probes)==len(resource_timeline) and
              [row['tick'] for row in self._fair_probes]==
                  [row['tick'] for row in resource_timeline],
              'v2n protected tick trace diverges from native-derived source')
        self._fair_progress=[row['forward_computations'] for row in resource_timeline]
        super().finish(next_native_tick,resource_timeline)

    def fairness_probes(self):
        self.priority_probes()
        guard(self._finished and
              len(self._fair_progress)==len(self._fair_probes)==
                  self._original_native_rows,
              'v2n incomplete forward fairness evidence')
        streak=0
        result=[]
        limit=self.fairness_plan.max_consecutive_actor_ticks_with_ready_forward
        for fair,pre,progress in zip(self._fair_probes,
                                     self._pre_probes,self._fair_progress):
            ready=fair['ready_forward_batches']
            protect=bool(ready) and streak>=limit
            reservation=(self.fairness_plan.protected_forward_pe_slots
                         if protect else 0)
            allowance=(self._caps[3]-reservation if protect
                       else self.plan.max_per_tick)
            grants=pre['pre_forward_actor_control_grants']
            new_streak=(0 if not ready or protect or not grants else
                        streak+1)
            guard(type(progress) is int and progress>=0 and
                  type(ready) is int and ready>=0 and
                  fair['tick']==pre['tick'] and
                  fair['ready_forward_batches']==
                      pre['ready_forward_batches_before_arbitration'] and
                  fair['actor_streak_before']==streak and
                  fair['actor_streak_after']==new_streak and
                  fair['protected_forward_opportunity'] is protect and
                  fair['reserved_forward_pe_slots']==reservation and
                  fair['control_pregrant_allowance']==allowance and
                  fair['actor_pregrants']==grants and grants<=allowance and
                  (not protect or grants<=self._caps[3]-reservation),
                  'v2n forward fairness probe or reserved PE grant forged')
            result.append({**fair,'forward_batches_committed':progress})
            streak=new_streak
        guard(streak==self._fair_streak,
              'v2n final forward fairness streak state drift')
        return result

    def project_original_native_result(self,derived_result):
        """Refuse a post-execution forgery of the forward-progress witness."""
        guard(self._finished and type(derived_result) is dict and
              type(derived_result.get('forward')) is dict and
              type(derived_result['forward'].get('batches')) is list and
              type(derived_result.get('resources')) is dict and
              type(derived_result['resources'].get('timeline')) is list and
              len(derived_result['resources']['timeline'])>=
                  self._original_native_rows,
              'v2n forward progress source evidence not available')
        guard(all(type(b) is dict and type(b.get('tick')) is int
                  for b in derived_result['forward']['batches']),
              'v2n forged forward batch tick type')
        batch_ticks=Counter(b['tick'] for b in derived_result['forward']['batches'])
        native_rows=derived_result['resources']['timeline'][:self._original_native_rows]
        guard(len(batch_ticks)==len([x for x in self._fair_progress if x>0]) and
              all(row['tick']==probe['tick'] and
                  type(row.get('forward_computations')) is int and
                  row['forward_computations']==progress==batch_ticks[probe['tick']]
                  for row,probe,progress in zip(native_rows,self._fair_probes,
                                                self._fair_progress)) and
              sum(self._fair_progress)==len(derived_result['forward']['batches']),
              'v2n unaccounted forward batches or forged protected tick progress')
        return super().project_original_native_result(derived_result)

    def summary(self):
        parent=super().summary()
        rows=self.fairness_probes()
        protected=[r for r in rows if r['protected_forward_opportunity']]
        return {
            **parent,'schema':FAIRNESS_SCHEMA,
            'max_consecutive_actor_ticks_with_ready_forward':
                self.fairness_plan.max_consecutive_actor_ticks_with_ready_forward,
            'protected_forward_pe_slots':self.fairness_plan.protected_forward_pe_slots,
            'protected_forward_opportunity_ticks':len(protected),
            'protected_opportunities_with_actual_forward_progress':sum(
                r['forward_batches_committed']>0 for r in protected),
            'protected_opportunities_without_forward_progress':sum(
                r['forward_batches_committed']==0 for r in protected),
            'max_observed_competing_actor_streak':max(
                (r['actor_streak_after'] for r in rows),default=0),
            'fairness_guarantee_is_budget_opportunity_only':True,
            'bounded_forward_completion_for_arbitrary_workloads_proven':False,
        }


def derive_fair_executor(source:bytes,original,port:ReceiverPortV2h,
                         fairness:DerivedActorFairnessV2n,
                         observer:CallsiteObserver):
    """Identical source-pinned hooks to v2m, but strict v2n adapter type."""
    guard(type(port) is ReceiverPortV2h and
          type(fairness) is DerivedActorFairnessV2n and
          fairness.port is port and type(observer) is CallsiteObserver and
          isinstance(original,FunctionType) and
          original.__name__=='execute_live_v0e',
          'v2n invalid source-pinned fairness compiler binding')
    node,callsites=audited_function(source)
    pre=_PreForwardInstrument()
    transformed=pre.visit(node)
    guard(pre.found==[PRE_FORWARD_ANCHOR],
          'v2n source-pinned pre-forward arbitration site changed')
    resource=_IntegratedAdmissionInstrument()
    transformed=resource.visit(transformed)
    guard(resource.inline==[INLINE_ANCHOR] and
          resource.finish==[FINISH_ANCHOR],
          'v2n source-pinned resource charge/tail hooks changed')
    ast.fix_missing_locations(transformed)
    semantic=_PortInstrument()
    transformed=semantic.visit(transformed)
    guard(tuple(sorted(semantic.found))==tuple(sorted(ANCHORS)),
          'v2n causal actor/receiver hooks changed')
    callsite=_Instrument()
    transformed=callsite.visit(transformed)
    guard(callsite.count==len(EXPECTED_CALLS),
          'v2n inherited pinned native callsite inventory changed')
    module=ast.Module(body=[ast.ImportFrom(module='__future__',
        names=[ast.alias(name='annotations')],level=0),transformed],type_ignores=[])
    ast.fix_missing_locations(module)
    namespace=dict(original.__globals__)
    native_admit=namespace['_admit']

    def bind_admit(*args,**kwargs):
        admitted=native_admit(*args,**kwargs)
        guard(type(admitted) is tuple and len(admitted)==2,
              'v2n frozen actor admission signature drift')
        fairness.bind_admitted_actors(*admitted)
        return admitted

    def wrap(name,line,callee_fn):
        guard(callable(callee_fn),'v2n noncallable source callsite')
        def inner(*args,**kwargs):
            try:
                result=callee_fn(*args,**kwargs)
            except BaseException:
                observer.emit(name,line,False)
                raise
            observer.emit(name,line,True)
            return result
        return inner

    namespace['_admit']=bind_admit
    namespace['__v2h_port']=port
    namespace['__v2k_admission']=fairness
    namespace['__v2m_priority']=fairness
    namespace['__spk_v2g_wrap']=wrap
    exec(compile(module,'<spk-v2n-derived-protected-forward-opportunity>',
                 'exec'),namespace)
    derived=namespace['execute_live_v0e']
    guard(derived is not original and
          derived.__code__.co_varnames[:7]==original.__code__.co_varnames[:7] and
          '__v2m_priority' not in original.__globals__ and
          '__v2k_admission' not in original.__globals__,
          'v2n derived fairness compilation contaminated frozen native')
    return derived,callsites,tuple(sorted(semantic.found)),(
        PRE_FORWARD_ANCHOR,INLINE_ANCHOR,FINISH_ANCHOR)
