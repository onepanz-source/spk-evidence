"""BV v2m: derived actor-first service competes with forward PE/memory grants.

The frozen scheduler source is compiled into a separate function with a
source-pinned pre-forward hook. Unlike v2l's after-forward-only accounting,
actor-first grants actually reduce available PE/memory budgets before the
native-derived forward batching loop. This can change its event schedule.

The native original is executed separately. A resource-only cost projection
is valid as an equality oracle ONLY if independent full native results match;
it must not relabel pre-forward contention as native parity or learning.
"""
from __future__ import annotations

import ast
from collections import Counter
from types import FunctionType

from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver,EXPECTED_CALLS,_Instrument,audited_function,guard,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import (
    ANCHORS,ReceiverPortV2h,_PortInstrument,
)
from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import (
    ActorCreditPlanV2l,DerivedActorCreditProtocolV2l,
)
from spk_backvalidation_v2.derived_actor_control_service_v2j import (
    ShadowServicePlanV2j,
)
from spk_backvalidation_v2.derived_actor_admission_v2k import (
    _IntegratedAdmissionInstrument,INLINE_ANCHOR,FINISH_ANCHOR,
)

PRIORITY_SCHEMA='spk-bv-derived-actor-event-resource-priority/research-v2m'
PRE_FORWARD_ANCHOR=158
PRIORITIES=('forward-first','actor-first')


def _subtract_charge(counter,charge):
    residual=Counter(counter)
    for key,count in charge.items():
        residual[key]-=count
    guard(all(value>=0 for value in residual.values()),
          'v2m forged pre-forward grant exceeds derived resource counter')
    return dict(sorted((key,value) for key,value in residual.items() if value>0))


class DerivedActorPriorityV2m(DerivedActorCreditProtocolV2l):
    def __init__(self,port:ReceiverPortV2h,*,priority:str,
                 credit_plan:ActorCreditPlanV2l=ActorCreditPlanV2l(),
                 service_plan:ShadowServicePlanV2j=ShadowServicePlanV2j()):
        guard(type(priority) is str and priority in PRIORITIES,
              'v2m unsupported explicit actor event priority')
        super().__init__(port,credit_plan,service_plan)
        self.priority=priority
        self._pre_grants:dict[int,tuple]={}
        self._pre_probes:list[dict]=[]
        self._pre_order:list[int]=[]

    def pre_forward_tick(self,tick,service_used,pe_total,mem_pe_used,
                         mem_dom_used,mem_total,owners,pe_caps,mem_pe_caps,
                         mem_domain_caps,pplan,mplan,pending,outboxes):
        guard(not self._closed and not self._finished and
              self._bound and not self.port._closed and
              self.port._clock==tick and type(tick) is int and
              tick not in self._pre_grants and
              type(service_used) is Counter and
              type(mem_pe_used) is Counter and
              type(mem_dom_used) is Counter and
              type(pe_total) is int and pe_total==0 and
              type(mem_total) is int and mem_total==0 and
              owners==self._owners and
              type(pending) is not type(None) and
              type(outboxes) is dict,
              'v2m pre-forward source ownership or zero-resource hook drift')
        ready=sorted((ready,actor) for (ready,actor) in pending
                     if ready<=tick and not outboxes[owners[actor]])
        eligible_before=sum(service_used[owners[actor]]<pe_caps[owners[actor]]
                            for _due,actor in ready)
        grants=()
        if self.priority=='actor-first':
            caps=(dict(pe_caps),dict(mem_pe_caps),dict(mem_domain_caps),
                  pplan.fabric_slots_per_tick,mplan.fabric_slots_per_tick)
            if self._caps is None:
                self._caps=caps
            guard(self._caps==caps and
                  (self._last_tick is None or tick>self._last_tick),
                  'v2m derived pre-forward capacity or tick drift')
            before=len(self._grants)
            self._service_tick(tick,'native-slack',service_used,pe_total,
                mem_pe_used,mem_dom_used,mem_total,*caps)
            grants=tuple(self._grants[before:])
            for grant in grants:
                service_used[grant.owner_pe]+=1
                mem_pe_used[grant.owner_pe]+=2
                mem_dom_used['O']+=1
                mem_dom_used['E']+=1
                pe_total+=1
                mem_total+=2
            row=self._timeline[-1]
            guard(row['combined_service_used']==pe_total and
                  row['combined_memory_used']==mem_total and
                  row['combined_service_by_pe']==dict(sorted(service_used.items())) and
                  row['combined_memory_by_pe']==dict(sorted(mem_pe_used.items())) and
                  row['combined_memory_by_domain']==dict(sorted(mem_dom_used.items())),
                  'v2m pre-forward PE/memory grant differs from actual counters')
        self._pre_grants[tick]=grants
        self._pre_order.append(tick)
        blocked=sum(pe_total>=pplan.fabric_slots_per_tick or
                    service_used[owners[actor]]>=pe_caps[owners[actor]]
                    for _due,actor in ready)
        self._pre_probes.append({
            'tick':tick,'ready_forward_batches_before_arbitration':len(ready),
            'eligible_forward_batches_before_pre_grants':eligible_before,
            'pre_forward_actor_control_grants':len(grants),
            'forward_batch_owners_blocked_by_pre_service_budget':blocked,
            'service_units_before_forward':pe_total,
            'memory_units_before_forward':mem_total,
        })
        return pe_total,mem_total

    def admit_tick(self,tick,service_used,pe_total,mem_pe_used,mem_dom_used,
                   mem_total,owners,pe_caps,mem_pe_caps,mem_domain_caps,pplan,mplan):
        guard(tick in self._pre_grants and
              self._pre_order==sorted(self._pre_order) and
              tick not in self._native_baselines,
              'v2m post-forward counter audit lacks unique pre-hook custody')
        if self.priority=='forward-first':
            guard(not self._pre_grants[tick],
                  'v2m forward-first policy illegally reserved early control')
            return super().admit_tick(tick,service_used,pe_total,mem_pe_used,
                mem_dom_used,mem_total,owners,pe_caps,mem_pe_caps,
                mem_domain_caps,pplan,mplan)
        guard(self._last_tick==tick and self._timeline[-1]['tick']==tick and
              self._timeline[-1]['phase']=='native-slack' and
              owners==self._owners and
              type(service_used) is Counter and
              type(mem_pe_used) is Counter and
              type(mem_dom_used) is Counter,
              'v2m actor-first post-forward resource source contract drift')
        grants=self._pre_grants[tick]
        pe_charge=Counter(g.owner_pe for g in grants)
        mem_charge=Counter({pe:2*count for pe,count in pe_charge.items()})
        dom_charge=Counter({'O':len(grants),'E':len(grants)})
        guard(pe_total>=len(grants) and mem_total>=2*len(grants),
              'v2m post-forward counters lost committed actor priority charges')
        baseline={
            'pe_service_total':pe_total-len(grants),
            'pe_service_by_pe':_subtract_charge(service_used,pe_charge),
            'memory_total':mem_total-2*len(grants),
            'memory_by_pe':_subtract_charge(mem_pe_used,mem_charge),
            'memory_by_domain':_subtract_charge(mem_dom_used,dom_charge),
        }
        self._native_baselines[tick]=baseline
        self._inline_grants[tick]=grants
        row=self._timeline[-1]
        row.update({
            'native_service_used':baseline['pe_service_total'],
            'native_memory_used':baseline['memory_total'],
            'combined_service_used':pe_total,
            'combined_memory_used':mem_total,
            'combined_service_by_pe':dict(sorted(service_used.items())),
            'combined_memory_by_pe':dict(sorted(mem_pe_used.items())),
            'combined_memory_by_domain':dict(sorted(mem_dom_used.items())),
        })
        guard(pe_total<=pplan.fabric_slots_per_tick and
              mem_total<=mplan.fabric_slots_per_tick and
              all(service_used[pe]<=limit for pe,limit in pe_caps.items()) and
              all(mem_pe_used[pe]<=limit for pe,limit in mem_pe_caps.items()) and
              all(mem_dom_used[domain]<=limit for domain,limit in mem_domain_caps.items()),
              'v2m actor-first priority oversubscribed real derived counters')
        return pe_total,mem_total

    def priority_probes(self):
        guard(self._finished and len(self._pre_probes)==self._original_native_rows,
              'v2m incomplete pre-forward priority trace')
        guard(self._pre_order==list(self._native_baselines) and
              all(type(row) is dict and
                  row['tick']==tick and
                  row['pre_forward_actor_control_grants']==len(self._pre_grants[tick]) and
                  row['service_units_before_forward']==len(self._pre_grants[tick]) and
                  row['memory_units_before_forward']==2*len(self._pre_grants[tick]) and
                  0<=row['eligible_forward_batches_before_pre_grants']<=
                      row['ready_forward_batches_before_arbitration'] and
                  0<=row['forward_batch_owners_blocked_by_pre_service_budget']<=
                      row['eligible_forward_batches_before_pre_grants']
                  for tick,row in zip(self._pre_order,self._pre_probes)),
              'v2m unaccounted pre-forward pressure-witness modification')
        return [dict(item) for item in self._pre_probes]

    def summary(self):
        inherited=super().summary()
        self.priority_probes()
        pre=sum(len(grants) for grants in self._pre_grants.values())
        pressure=sum(row['forward_batch_owners_blocked_by_pre_service_budget']
                     for row in self._pre_probes)
        guard(pre==(inherited['derived_inline_actor_grants']
                    if self.priority=='actor-first' else 0) and
              len(self._pre_probes)==self._original_native_rows and
              (self.priority=='actor-first' or pressure==0),
              'v2m derived actor event priority phase/grant custody drift')
        return {
            **inherited,'schema':PRIORITY_SCHEMA,'actor_event_priority':self.priority,
            'pre_forward_actor_grants':pre,
            'ready_forward_batches_blocked_by_pre_grants':pressure,
            'ticks_with_both_pre_control_and_ready_forward':sum(
                row['pre_forward_actor_control_grants']>0 and
                row['eligible_forward_batches_before_pre_grants']>0
                for row in self._pre_probes),
            'derived_preemptive_only_between_atomic_forward_batches':True,
            'frozen_native_event_priority_policy_modified':False,
        }


class _PreForwardInstrument(ast.NodeTransformer):
    def __init__(self):
        self.found=[]

    def visit_While(self,node):
        self.generic_visit(node)
        if node.lineno!=PRE_FORWARD_ANCHOR:
            return node
        guard(isinstance(node.test,ast.Constant) and node.test.value is True,
              'v2m native batch arbitration while-test changed')
        names=('now','service_used','pe_total','mem_pe_used','mem_dom_used',
               'mem_total','owners','pe_caps','mem_pe_caps','mem_domain_caps',
               'pplan','mplan','pending','outboxes')
        hook=ast.Assign(targets=[ast.Tuple(elts=[
            ast.Name(id='pe_total',ctx=ast.Store()),
            ast.Name(id='mem_total',ctx=ast.Store())],ctx=ast.Store())],
            value=ast.Call(func=ast.Attribute(
                value=ast.Name(id='__v2m_priority',ctx=ast.Load()),
                attr='pre_forward_tick',ctx=ast.Load()),
                args=[ast.Name(id=n,ctx=ast.Load()) for n in names],keywords=[]))
        self.found.append(node.lineno)
        return [hook,node]


def derive_priority_executor(source:bytes,original,port:ReceiverPortV2h,
                             priority:DerivedActorPriorityV2m,
                             observer:CallsiteObserver):
    guard(type(port) is ReceiverPortV2h and
          type(priority) is DerivedActorPriorityV2m and
          priority.port is port and type(observer) is CallsiteObserver and
          isinstance(original,FunctionType) and
          original.__name__=='execute_live_v0e',
          'v2m invalid derived native priority adapter controls')
    node,callsites=audited_function(source)
    hook=_PreForwardInstrument()
    transformed=hook.visit(node)
    guard(hook.found==[PRE_FORWARD_ANCHOR],
          'v2m missing unique source-pinned forward arbitration site')
    resource=_IntegratedAdmissionInstrument()
    transformed=resource.visit(transformed)
    guard(resource.inline==[INLINE_ANCHOR] and
          resource.finish==[FINISH_ANCHOR],
          'v2m source-pinned derived resource/tail hooks changed')
    ast.fix_missing_locations(transformed)
    semantic=_PortInstrument()
    transformed=semantic.visit(transformed)
    guard(tuple(sorted(semantic.found))==tuple(sorted(ANCHORS)),
          'v2m native causal emission/ingress/receiver anchors changed')
    callee=_Instrument()
    transformed=callee.visit(transformed)
    guard(callee.count==len(EXPECTED_CALLS),
          'v2m inherited native callsite inventory changed')
    module=ast.Module(body=[ast.ImportFrom(module='__future__',
        names=[ast.alias(name='annotations')],level=0),transformed],type_ignores=[])
    ast.fix_missing_locations(module)
    namespace=dict(original.__globals__)
    native_admit=namespace['_admit']

    def bind_admission(*args,**kwargs):
        result=native_admit(*args,**kwargs)
        guard(type(result) is tuple and len(result)==2,
              'v2m native actor owner admission result changed')
        priority.bind_admitted_actors(*result)
        return result

    def wrap(name,line,callee_fn):
        guard(callable(callee_fn),'v2m noncallable pinned callsite')
        def inner(*args,**kwargs):
            try:
                result=callee_fn(*args,**kwargs)
            except BaseException:
                observer.emit(name,line,False)
                raise
            observer.emit(name,line,True)
            return result
        return inner

    namespace['_admit']=bind_admission
    namespace['__v2h_port']=port
    namespace['__v2k_admission']=priority
    namespace['__v2m_priority']=priority
    namespace['__spk_v2g_wrap']=wrap
    exec(compile(module,'<spk-v2m-derived-pre-forward-priority>','exec'),namespace)
    derived=namespace['execute_live_v0e']
    guard(derived is not original and
          derived.__code__.co_varnames[:7]==original.__code__.co_varnames[:7] and
          '__v2m_priority' not in original.__globals__,
          'v2m derived priority source contaminated frozen scheduler')
    return derived,callsites,tuple(sorted(semantic.found)),(
        PRE_FORWARD_ANCHOR,INLINE_ANCHOR,FINISH_ANCHOR)
