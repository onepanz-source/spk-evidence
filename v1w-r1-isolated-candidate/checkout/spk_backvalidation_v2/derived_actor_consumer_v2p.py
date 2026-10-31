"""BV v2p: explicitly consume derived, resource-ACKed actor credits.

ACK != consumer application. The consumer has its own actor-scoped state,
ordered receipts, replay protection and bounded backlog. It borrows the
earlier resource-charged ACK entitlement; NO extra PE charge is asserted for
applying the credit. This research actor state never modifies frozen neurons.
"""
from __future__ import annotations

import ast
import json
from dataclasses import asdict,dataclass,replace
from hashlib import sha256
from types import FunctionType

from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver,EXPECTED_CALLS,_Instrument,audited_function,guard,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import (
    ANCHORS,ReceiverPortV2h,_PortInstrument,
)
from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import (
    ActorCreditPlanV2l,ZERO_ROOT,
)
from spk_backvalidation_v2.derived_actor_control_service_v2j import ShadowServicePlanV2j
from spk_backvalidation_v2.derived_actor_admission_v2k import (
    _IntegratedAdmissionInstrument,INLINE_ANCHOR,FINISH_ANCHOR,
)
from spk_backvalidation_v2.derived_actor_priority_v2m import PRE_FORWARD_ANCHOR
from spk_backvalidation_v2.derived_causal_admission_v2o import (
    CausalAdmissionPlanV2o,DerivedCausalAdmissionV2o,
    _NativeCausalPreForwardInstrument,
)

CONSUMER_SCHEMA='spk-bv-derived-actor-ack-consumer-handoff/research-v2p'


@dataclass(frozen=True,slots=True)
class ActorConsumerPlanV2p:
    max_consume_per_tick: int = 1
    max_tail_ticks: int = 32
    max_total_consume: int = 512
    max_pending_ack_backlog: int = 512


@dataclass(frozen=True,slots=True)
class ActorConsumptionV2p:
    actor: str
    owner_pe: str
    consumer_seq: int
    ack_seq: int
    judgment_id: str
    source_emission: str
    ack_digest: str
    response: int
    ack_service_tick: int
    consume_tick: int
    consume_phase: str
    applied_credit_before: int
    applied_credit_after: int
    chain_prev: str
    chain_digest: str


def _consume_digest(receipt):
    payload=asdict(replace(receipt,chain_digest=''))
    return sha256(json.dumps(payload,sort_keys=True,ensure_ascii=True,
                separators=(',',':')).encode('utf8')).hexdigest()


class DerivedActorConsumerV2p(DerivedCausalAdmissionV2o):
    """A distinct derived consumer turn after the v2l grant/ACK journal.

    Consumer applications are FIFO over all ACKs, actor-owned and monotone.
    No application may precede its original resource service tick. Truncated
    capacity/quota leaves observable pending ACKs, never silence proofs.
    """

    def __init__(self,port:ReceiverPortV2h,*,
                 consumer_plan:ActorConsumerPlanV2p=ActorConsumerPlanV2p(),
                 admission_plan:CausalAdmissionPlanV2o=CausalAdmissionPlanV2o(),
                 credit_plan:ActorCreditPlanV2l=ActorCreditPlanV2l(),
                 service_plan:ShadowServicePlanV2j=ShadowServicePlanV2j()):
        guard(type(consumer_plan) is ActorConsumerPlanV2p and
              all(type(v) is int for v in (
                  consumer_plan.max_consume_per_tick,
                  consumer_plan.max_tail_ticks,
                  consumer_plan.max_total_consume,
                  consumer_plan.max_pending_ack_backlog)) and
              0<=consumer_plan.max_consume_per_tick<=16 and
              0<=consumer_plan.max_tail_ticks<=128 and
              0<=consumer_plan.max_total_consume<=512 and
              0<=consumer_plan.max_pending_ack_backlog<=512,
              'v2p invalid bounded actor ACK consumer contract')
        super().__init__(port,admission_plan=admission_plan,
                         credit_plan=credit_plan,service_plan=service_plan)
        self.consumer_plan=consumer_plan
        self._applied_credit={}
        self._consumer_seq={}
        self._consumer_roots={}
        self._consume_journal=[]
        self._consume_trace=[]
        self._last_consume_tick=None
        self._consumer_tail_ticks=0

    def bind_admitted_actors(self,nodes,owners):
        super().bind_admitted_actors(nodes,owners)
        self._applied_credit={actor:0 for actor in sorted(nodes)}
        self._consumer_seq={actor:0 for actor in sorted(nodes)}
        self._consumer_roots={actor:ZERO_ROOT for actor in sorted(nodes)}

    def _bounded_backlog(self):
        size=len(self._acks)-len(self._consume_journal)
        guard(0<=size<=self.consumer_plan.max_pending_ack_backlog,
              'v2p derived actor consumer ACK mailbox overflow fail-closed')
        return size

    def _consume_tick(self,tick,phase):
        guard(type(tick) is int and
              phase in ('after-native-forward','derived-consumer-tail') and
              self._bound and
              (self._last_consume_tick is None or tick>self._last_consume_tick),
              'v2p invalid actor consumer tick or replayed causal phase')
        self._last_consume_tick=tick
        consumed=[]
        limit=min(self.consumer_plan.max_consume_per_tick,
                  self.consumer_plan.max_total_consume-len(self._consume_journal))
        self._bounded_backlog()
        if limit:
            for ack in self._acks[len(self._consume_journal):]:
                if len(consumed)>=limit or ack.serviced_tick>tick:
                    break
                actor=ack.actor
                guard(ack.owner_pe==self._owners[actor] and
                      ack.judgment_id in self._acked_ids and
                      ack.serviced_tick>=ack.due_tick and
                      ack.response in (-1,1) and
                      len(consumed)<limit,
                      'v2p actor consumer ACK lacks prior causal PE service')
                before=self._applied_credit[actor]
                after=before+ack.response
                # The v2l ACK register is independent and remains bounded.
                guard(abs(after)<=512,
                      'v2p actor consumer state cannot exceed v2l credit envelope')
                event=ActorConsumptionV2p(
                    actor=actor,owner_pe=ack.owner_pe,
                    consumer_seq=self._consumer_seq[actor]+1,
                    ack_seq=ack.seq,judgment_id=ack.judgment_id,
                    source_emission=ack.source_emission,
                    ack_digest=ack.chain_digest,response=ack.response,
                    ack_service_tick=ack.serviced_tick,consume_tick=tick,
                    consume_phase=phase,applied_credit_before=before,
                    applied_credit_after=after,
                    chain_prev=self._consumer_roots[actor],chain_digest='')
                event=replace(event,chain_digest=_consume_digest(event))
                self._applied_credit[actor]=after
                self._consumer_seq[actor]=event.consumer_seq
                self._consumer_roots[actor]=event.chain_digest
                self._consume_journal.append(event)
                consumed.append(event)
        remaining=self._bounded_backlog()
        self._consume_trace.append({
            'tick':tick,'phase':phase,
            'acks_available_before_consumer':remaining+len(consumed),
            'actor_consumer_applications':len(consumed),
            'ack_backlog_after_consumer':remaining,
            'consumer_extra_pe_service_units':0,
            'consumer_extra_memory_units':0,
        })

    def admit_tick(self,*args,**kwargs):
        result=super().admit_tick(*args,**kwargs)
        self._consume_tick(args[0],'after-native-forward')
        return result

    def finish(self,next_native_tick,resource_timeline):
        super().finish(next_native_tick,resource_timeline)
        self._bounded_backlog()
        last_tick=max(row['tick'] for row in self._timeline)
        for step in range(1,self.consumer_plan.max_tail_ticks+1):
            if (len(self._consume_journal)==len(self._acks) or
                    len(self._consume_journal)>=self.consumer_plan.max_total_consume or
                    self.consumer_plan.max_consume_per_tick==0):
                break
            # Source-closed actor-local turns: no synthetic forward computation
            # or PE charge, and never relabelled as native timeline ticks.
            self._consume_tick(last_tick+step,'derived-consumer-tail')
            self._consumer_tail_ticks+=1
        self._bounded_backlog()

    def audit_consumer(self):
        self.audit_credit()
        source_ticks=[row['tick'] for row in self._timeline
                      if row['phase']!='post-native-tail']
        tail_start=self._timeline[-1]['tick']
        expected_trace=[(tick,'after-native-forward') for tick in source_ticks]
        expected_trace.extend((tail_start+i,'derived-consumer-tail')
                              for i in range(1,self._consumer_tail_ticks+1))
        guard(self._finished and len(self._consume_journal)<=len(self._acks) and
              len(self._consume_journal)<=self.consumer_plan.max_total_consume and
              self._consumer_tail_ticks<=self.consumer_plan.max_tail_ticks and
              len(source_ticks)==self._original_native_rows and
              [(row['tick'],row['phase']) for row in self._consume_trace]==
                  expected_trace and
              self._consume_trace and
              self._consumer_tail_ticks==sum(row['phase']=='derived-consumer-tail'
                  for row in self._consume_trace) and
              all(row['consumer_extra_pe_service_units']==0 and
                  row['consumer_extra_memory_units']==0 and
                  row['acks_available_before_consumer']==
                      row['actor_consumer_applications']+
                      row['ack_backlog_after_consumer']
                  for row in self._consume_trace),
              'v2p consumer phase/backlog resource custody drift')
        balances={actor:0 for actor in self._actors}
        epochs={actor:0 for actor in self._actors}
        roots={actor:ZERO_ROOT for actor in self._actors}
        last_tick=None
        for ack,receipt in zip(self._acks,self._consume_journal):
            actor=ack.actor
            after=balances[actor]+ack.response
            guard(receipt.actor==actor and
                  receipt.owner_pe==ack.owner_pe==self._owners[actor] and
                  receipt.ack_seq==ack.seq and
                  receipt.judgment_id==ack.judgment_id and
                  receipt.source_emission==ack.source_emission and
                  receipt.ack_digest==ack.chain_digest and
                  receipt.response==ack.response and
                  receipt.ack_service_tick==ack.serviced_tick and
                  receipt.consume_tick>=ack.serviced_tick and
                  receipt.consume_phase in (
                      'after-native-forward','derived-consumer-tail') and
                  receipt.consumer_seq==epochs[actor]+1 and
                  receipt.applied_credit_before==balances[actor] and
                  receipt.applied_credit_after==after and
                  receipt.chain_prev==roots[actor] and
                  receipt.chain_digest==_consume_digest(receipt) and
                  (last_tick is None or receipt.consume_tick>=last_tick),
                  'v2p consumer forged, replayed, reordered or misbound actor ACK')
            balances[actor]=after
            epochs[actor]+=1
            roots[actor]=receipt.chain_digest
            last_tick=receipt.consume_tick
        applied_index=0
        for row in self._consume_trace:
            tick,phase=row['tick'],row['phase']
            consumed=row['actor_consumer_applications']
            total_available=sum(ack.serviced_tick<=tick for ack in self._acks)
            remaining=total_available-applied_index-consumed
            relevant=self._consume_journal[applied_index:applied_index+consumed]
            guard(type(consumed) is int and
                  0<=consumed<=self.consumer_plan.max_consume_per_tick and
                  row['acks_available_before_consumer']==
                      total_available-applied_index and
                  row['ack_backlog_after_consumer']==remaining and
                  all(entry.consume_tick==tick and entry.consume_phase==phase
                      for entry in relevant) and
                  remaining>=0,
                  'v2p consumer forged tick, throughput, due order or backlog')
            applied_index+=consumed
        guard(balances==self._applied_credit and
              epochs==self._consumer_seq and
              roots==self._consumer_roots and
              applied_index==len(self._consume_journal) and
              sum(row['actor_consumer_applications']
                  for row in self._consume_trace)==len(self._consume_journal) and
              self._bounded_backlog()==len(self._acks)-len(self._consume_journal),
              'v2p consumer applied state or exactly-once journal mismatch')
        return True

    def project_original_native_result(self,derived_result):
        self.audit_consumer()
        return super().project_original_native_result(derived_result)

    def consumer_journal(self):
        self.audit_consumer()
        return [asdict(entry) for entry in self._consume_journal]

    def consumer_trace(self):
        self.audit_consumer()
        return [dict(row) for row in self._consume_trace]

    def summary(self):
        original=super().summary()
        self.audit_consumer()
        return {
            **original,'schema':CONSUMER_SCHEMA,
            'actor_consumer_applications':len(self._consume_journal),
            'actor_consumer_pending_ack_backlog':self._bounded_backlog(),
            'actor_consumer_applied_credit':dict(sorted(self._applied_credit.items())),
            'actor_consumer_application_epochs':dict(sorted(self._consumer_seq.items())),
            'actor_consumer_chain_roots':dict(sorted(self._consumer_roots.items())),
            'consumer_native_tick_applications':sum(
                x.consume_phase=='after-native-forward' for x in self._consume_journal),
            'consumer_tail_applications':sum(
                x.consume_phase=='derived-consumer-tail' for x in self._consume_journal),
            'consumer_extra_tail_ticks':self._consumer_tail_ticks,
            'consumer_max_per_tick':self.consumer_plan.max_consume_per_tick,
            'consumer_max_total':self.consumer_plan.max_total_consume,
            'consumer_backlog_limit':self.consumer_plan.max_pending_ack_backlog,
            'consumer_consumption_borrows_existing_ACK_charge':True,
            'consumer_extra_PE_or_memory_budget_charged':False,
            'real_frozen_native_actor_consumer_changed':False,
            'real_frozen_native_learning_proven':False,
        }


def derive_consumer_executor(source:bytes,original,port:ReceiverPortV2h,
                            consumer:DerivedActorConsumerV2p,
                            observer:CallsiteObserver):
    guard(type(port) is ReceiverPortV2h and
          type(consumer) is DerivedActorConsumerV2p and
          consumer.port is port and type(observer) is CallsiteObserver and
          isinstance(original,FunctionType) and
          original.__name__=='execute_live_v0e',
          'v2p invalid derived actor consumer source compiler controls')
    node,callsites=audited_function(source)
    pre=_NativeCausalPreForwardInstrument()
    transformed=pre.visit(node)
    guard(pre.found==[PRE_FORWARD_ANCHOR],
          'v2p pinned native-ready event-precedence hook drift')
    resource=_IntegratedAdmissionInstrument()
    transformed=resource.visit(transformed)
    guard(resource.inline==[INLINE_ANCHOR] and
          resource.finish==[FINISH_ANCHOR],
          'v2p actor-consumer tick/closure source anchors drift')
    ast.fix_missing_locations(transformed)
    semantic=_PortInstrument()
    transformed=semantic.visit(transformed)
    guard(tuple(sorted(semantic.found))==tuple(sorted(ANCHORS)),
          'v2p native source actor/receiver semantic hook drift')
    callsite=_Instrument()
    transformed=callsite.visit(transformed)
    guard(callsite.count==len(EXPECTED_CALLS),
          'v2p frozen callsite source inventory drift')
    module=ast.Module(body=[ast.ImportFrom(module='__future__',
        names=[ast.alias(name='annotations')],level=0),transformed],type_ignores=[])
    ast.fix_missing_locations(module)
    namespace=dict(original.__globals__)
    native_admit=namespace['_admit']

    def bind_admit(*args,**kwargs):
        result=native_admit(*args,**kwargs)
        guard(type(result) is tuple and len(result)==2,
              'v2p frozen native actor ownership source contract changed')
        consumer.bind_admitted_actors(*result)
        return result

    def wrap(name,line,callee_fn):
        guard(callable(callee_fn),'v2p invalid source audited callee')
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
    namespace['__v2k_admission']=consumer
    namespace['__v2o_causal_admission']=consumer
    namespace['__spk_v2g_wrap']=wrap
    exec(compile(module,'<spk-v2p-derived-actor-consumer-handoff>','exec'),namespace)
    derived=namespace['execute_live_v0e']
    guard(derived is not original and
          derived.__code__.co_varnames[:7]==original.__code__.co_varnames[:7] and
          '__v2o_causal_admission' not in original.__globals__ and
          '__v2k_admission' not in original.__globals__,
          'v2p consumer source compiler mutated frozen scheduler globals')
    return derived,callsites,tuple(sorted(semantic.found)),(
        PRE_FORWARD_ANCHOR,INLINE_ANCHOR,FINISH_ANCHOR)
