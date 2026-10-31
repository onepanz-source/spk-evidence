"""BV v2o: native-causal-ready work has precedence over derived actor controls.

The reservation is a testable, derived-only schedule contract. A source-pinned
hook observes ready forward batches and *already ready* native BV packets
before any derived actor-control grant. No native operator or actor mutates.
"""
from __future__ import annotations

import ast
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
from spk_backvalidation_v2.derived_actor_priority_v2m import PRE_FORWARD_ANCHOR
from spk_backvalidation_v2.derived_actor_fairness_v2n import (
    FairnessPlanV2n,DerivedActorFairnessV2n,
)

ADMISSION_SCHEMA='spk-bv-derived-native-causal-work-admission/research-v2o'


@dataclass(frozen=True,slots=True)
class CausalAdmissionPlanV2o:
    protect_ready_forward: bool = True
    protect_ready_native_feedback: bool = True


class DerivedCausalAdmissionV2o(DerivedActorFairnessV2n):
    """Withhold actor credit pregrants during native causally due work.

    Strict mode vetoes early actor credit if ANY source-backed ready forward
    batch or ready native BV packet is present. This is intentionally more
    conservative than v2n's single reserved forward slot. Native BV packets
    still use the unmodified native link/scheduler arbitration.
    """

    def __init__(self,port:ReceiverPortV2h,*,
                 admission_plan:CausalAdmissionPlanV2o=CausalAdmissionPlanV2o(),
                 credit_plan:ActorCreditPlanV2l=ActorCreditPlanV2l(),
                 service_plan:ShadowServicePlanV2j=ShadowServicePlanV2j()):
        guard(type(admission_plan) is CausalAdmissionPlanV2o and
              type(admission_plan.protect_ready_forward) is bool and
              type(admission_plan.protect_ready_native_feedback) is bool,
              'v2o invalid explicit native causal service precedence contract')
        # v2o does its own causal-ready veto. A large admissible v2n window
        # gives an exact actor-first ablation when both vetoes are disabled.
        super().__init__(port,fairness_plan=FairnessPlanV2n(16),
                         credit_plan=credit_plan,service_plan=service_plan)
        self.admission_plan=admission_plan
        self._pre_native_causal_veto=False
        self._admission_probes=[]

    def _pending(self,tick):
        verified=super()._pending(tick)  # complete actor custody validation
        return [] if self._pre_allowance is not None and self._pre_native_causal_veto else verified

    def pre_forward_tick(self,tick,service_used,pe_total,mem_pe_used,
                         mem_dom_used,mem_total,owners,pe_caps,mem_pe_caps,
                         mem_domain_caps,pplan,mplan,pending,outboxes,
                         ready_feedback):
        guard(not self._pre_native_causal_veto and
              type(ready_feedback) is list and
              all(type(x) is dict and type(x.get('ready')) is int and
                  type(x.get('packet_id')) is str and
                  type(x.get('sender')) is str and
                  type(x.get('receiver')) is str
                  for x in ready_feedback),
              'v2o source-backed native ready-feedback inventory drift')
        ready_forward=sum(due<=tick and not outboxes[owners[actor]]
                          for due,actor in pending)
        native_bv_ready=sum(packet['ready']<=tick for packet in ready_feedback)
        forward_veto=bool(ready_forward) and self.admission_plan.protect_ready_forward
        feedback_veto=bool(native_bv_ready) and self.admission_plan.protect_ready_native_feedback
        veto=forward_veto or feedback_veto
        self._pre_native_causal_veto=veto
        try:
            result=super().pre_forward_tick(tick,service_used,pe_total,
                mem_pe_used,mem_dom_used,mem_total,owners,pe_caps,
                mem_pe_caps,mem_domain_caps,pplan,mplan,pending,outboxes)
        finally:
            self._pre_native_causal_veto=False
        grants=len(self._pre_grants[tick])
        guard(not veto or grants==0,
              'v2o derived actor control charged native-causally-ready tick')
        self._admission_probes.append({
            'tick':tick,
            'ready_forward_batches_before_actor_admission':ready_forward,
            'ready_native_feedback_packets_before_actor_admission':native_bv_ready,
            'forward_priority_veto':forward_veto,
            'native_feedback_priority_veto':feedback_veto,
            'native_causal_priority_veto':veto,
            'pre_forward_actor_credit_grants':grants,
        })
        return result

    def admission_probes(self):
        fair=self.fairness_probes()
        guard(len(fair)==len(self._admission_probes)==self._original_native_rows,
              'v2o incomplete source-observed native causal admission evidence')
        result=[]
        for row,base in zip(self._admission_probes,fair):
            forward=row['ready_forward_batches_before_actor_admission']
            native_bv=row['ready_native_feedback_packets_before_actor_admission']
            f_veto=bool(forward) and self.admission_plan.protect_ready_forward
            b_veto=bool(native_bv) and self.admission_plan.protect_ready_native_feedback
            veto=f_veto or b_veto
            guard(type(forward) is int and forward>=0 and
                  type(native_bv) is int and native_bv>=0 and
                  row['tick']==base['tick'] and
                  forward==base['ready_forward_batches'] and
                  row['forward_priority_veto'] is f_veto and
                  row['native_feedback_priority_veto'] is b_veto and
                  row['native_causal_priority_veto'] is veto and
                  row['pre_forward_actor_credit_grants']==base['actor_pregrants'] and
                  (not veto or base['actor_pregrants']==0),
                  'v2o forged actor admission native ready-work/veto trace')
            result.append({**row,
                'forward_batches_committed':base['forward_batches_committed']})
        return result

    def summary(self):
        base=super().summary()
        observed=self.admission_probes()
        protected=[x for x in observed if x['native_causal_priority_veto']]
        slack=[x for x in observed if not x['native_causal_priority_veto']]
        return {
            **base,'schema':ADMISSION_SCHEMA,
            'protect_ready_forward':self.admission_plan.protect_ready_forward,
            'protect_ready_native_feedback':
                self.admission_plan.protect_ready_native_feedback,
            'native_causal_priority_veto_ticks':len(protected),
            'native_forward_veto_ticks':sum(x['forward_priority_veto'] for x in observed),
            'native_feedback_veto_ticks':sum(x['native_feedback_priority_veto'] for x in observed),
            'admissible_actor_pregrant_ticks':len(slack),
            'pregrants_during_native_causal_veto':sum(
                x['pre_forward_actor_credit_grants'] for x in protected),
            'pregrants_during_no_native_causal_ready_work':sum(
                x['pre_forward_actor_credit_grants'] for x in slack),
            'native_event_arbitration_modified':False,
            'arbitrary_workload_deadline_parity_proven':False,
        }


class _NativeCausalPreForwardInstrument(ast.NodeTransformer):
    def __init__(self):
        self.found=[]

    def visit_While(self,node):
        self.generic_visit(node)
        if node.lineno!=PRE_FORWARD_ANCHOR:
            return node
        guard(isinstance(node.test,ast.Constant) and node.test.value is True,
              'v2o native batch arbitration while-test changed')
        names=('now','service_used','pe_total','mem_pe_used','mem_dom_used',
               'mem_total','owners','pe_caps','mem_pe_caps','mem_domain_caps',
               'pplan','mplan','pending','outboxes','ready_feedback')
        call=ast.Call(func=ast.Attribute(
            value=ast.Name(id='__v2o_causal_admission',ctx=ast.Load()),
            attr='pre_forward_tick',ctx=ast.Load()),
            args=[ast.Name(id=n,ctx=ast.Load()) for n in names],keywords=[])
        hook=ast.Assign(targets=[ast.Tuple(elts=[
            ast.Name(id='pe_total',ctx=ast.Store()),
            ast.Name(id='mem_total',ctx=ast.Store())],ctx=ast.Store())],value=call)
        self.found.append(node.lineno)
        return [hook,node]


def derive_causal_executor(source:bytes,original,port:ReceiverPortV2h,
                           admission:DerivedCausalAdmissionV2o,
                           observer:CallsiteObserver):
    guard(type(port) is ReceiverPortV2h and
          type(admission) is DerivedCausalAdmissionV2o and
          admission.port is port and type(observer) is CallsiteObserver and
          isinstance(original,FunctionType) and
          original.__name__=='execute_live_v0e',
          'v2o invalid independent native-causal admission source binding')
    node,callsites=audited_function(source)
    pre=_NativeCausalPreForwardInstrument()
    transformed=pre.visit(node)
    guard(pre.found==[PRE_FORWARD_ANCHOR],
          'v2o missing unique native causal-ready arbitration anchor')
    resource=_IntegratedAdmissionInstrument()
    transformed=resource.visit(transformed)
    guard(resource.inline==[INLINE_ANCHOR] and
          resource.finish==[FINISH_ANCHOR],
          'v2o native-derived PE/memory and tail anchors changed')
    ast.fix_missing_locations(transformed)
    receiver=_PortInstrument()
    transformed=receiver.visit(transformed)
    guard(tuple(sorted(receiver.found))==tuple(sorted(ANCHORS)),
          'v2o causal actor/receiver/source hook anchors changed')
    callsite=_Instrument()
    transformed=callsite.visit(transformed)
    guard(callsite.count==len(EXPECTED_CALLS),
          'v2o native-callsite source inventory changed')
    module=ast.Module(body=[ast.ImportFrom(module='__future__',
        names=[ast.alias(name='annotations')],level=0),transformed],type_ignores=[])
    ast.fix_missing_locations(module)
    namespace=dict(original.__globals__)
    frozen_admit=namespace['_admit']

    def bind_admit(*args,**kwargs):
        result=frozen_admit(*args,**kwargs)
        guard(type(result) is tuple and len(result)==2,
              'v2o frozen native actor owner admission result drift')
        admission.bind_admitted_actors(*result)
        return result

    def wrap(name,line,callee_fn):
        guard(callable(callee_fn),'v2o noncallable audited native callsite')
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
    namespace['__v2k_admission']=admission
    namespace['__v2o_causal_admission']=admission
    namespace['__spk_v2g_wrap']=wrap
    exec(compile(module,'<spk-v2o-derived-native-causal-actor-admission>',
                 'exec'),namespace)
    derived=namespace['execute_live_v0e']
    guard(derived is not original and
          derived.__code__.co_varnames[:7]==original.__code__.co_varnames[:7] and
          '__v2o_causal_admission' not in original.__globals__ and
          '__v2k_admission' not in original.__globals__,
          'v2o independent derived compiler contaminated frozen native')
    return derived,callsites,tuple(sorted(receiver.found)),(
        PRE_FORWARD_ANCHOR,INLINE_ANCHOR,FINISH_ANCHOR)
