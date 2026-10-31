"""BV v2l: bounded derived actor credit admission and exact-once ack journal.

An actor's research-only control register acknowledges only a causally
delivered and resource-serviced receiver judgment. Ledger entries bind the
admitted actor/PE, causal spike, issuer, decision, resource tick and a
per-actor monotonic sequence. An ordered hash chain detects accidental or
adversarial edits to the in-process audit, but is NOT authentication.

The frozen native actor state/learner is never modified or consulted. Policy
denial and transport silence never become negative judgments.
"""
from __future__ import annotations

import ast
import json
from collections import Counter
from dataclasses import asdict,dataclass,replace
from hashlib import sha256
from types import FunctionType

from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver,EXPECTED_CALLS,_Instrument,audited_function,guard,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import (
    ANCHORS,ReceiverPortV2h,_PortInstrument,
)
from spk_backvalidation_v2.derived_actor_control_service_v2j import (
    ShadowServicePlanV2j,
)
from spk_backvalidation_v2.derived_actor_admission_v2k import (
    DerivedActorAdmissionV2k,_IntegratedAdmissionInstrument,
    INLINE_ANCHOR,FINISH_ANCHOR,_tail_resource_row,
)

PROTOCOL_SCHEMA='spk-bv-derived-actor-credit-event-protocol/research-v2l'
ZERO_ROOT='0'*64


@dataclass(frozen=True,slots=True)
class ActorCreditPlanV2l:
    max_abs_credit: int = 256
    max_actor_acks_total: int = 512
    strict_due_fifo: bool = True


@dataclass(frozen=True,slots=True)
class ActorCreditAckV2l:
    actor: str
    owner_pe: str
    seq: int
    judgment_id: str
    source_emission: str
    receiver_issuer: str
    decision: str
    response: int
    created_tick: int
    due_tick: int
    serviced_tick: int
    resource_phase: str
    credit_before: int
    credit_after: int
    chain_prev: str
    chain_digest: str


def _digest_ack(ack:ActorCreditAckV2l):
    payload=asdict(replace(ack,chain_digest=''))
    return sha256(json.dumps(payload,sort_keys=True,ensure_ascii=True,
                separators=(',',':')).encode('utf-8')).hexdigest()


class DerivedActorCreditProtocolV2l(DerivedActorAdmissionV2k):
    """A separate, bounded actor-addressed credit register on top of v2k.

    Exactly one ack is recorded after each v2k counter-committed service
    grant. Over-limit events remain delivered but not consumed. Strict FIFO
    forbids bypassing an older blocked event for the same actor.
    """

    def __init__(self,port:ReceiverPortV2h,
                 credit_plan:ActorCreditPlanV2l=ActorCreditPlanV2l(),
                 service_plan:ShadowServicePlanV2j=ShadowServicePlanV2j()):
        guard(type(credit_plan) is ActorCreditPlanV2l and
              type(credit_plan.max_abs_credit) is int and
              0<=credit_plan.max_abs_credit<=512 and
              type(credit_plan.max_actor_acks_total) is int and
              0<=credit_plan.max_actor_acks_total<=512 and
              credit_plan.strict_due_fifo is True and
              type(service_plan) is ShadowServicePlanV2j and
              service_plan.per_actor_per_tick==1,
              'v2l invalid bounded FIFO actor credit policy')
        super().__init__(port,service_plan)
        self.credit_plan=credit_plan
        self._balance:dict[str,int]={}
        self._actor_seq:dict[str,int]={}
        self._actor_roots:dict[str,str]={}
        self._actor_last_order:dict[str,tuple[int,str]]={}
        self._acks:list[ActorCreditAckV2l]=[]
        self._acked_ids:set[str]=set()
        self._policy_blocked_ids:set[str]=set()

    def bind_admitted_actors(self,nodes,owners):
        super().bind_admitted_actors(nodes,owners)
        self._balance={actor:0 for actor in sorted(nodes)}
        self._actor_seq={actor:0 for actor in sorted(nodes)}
        self._actor_roots={actor:ZERO_ROOT for actor in sorted(nodes)}

    def _pending(self,tick):
        items=super()._pending(tick)  # validates all causal/actor custody first
        allowed=[]
        blocked_actors=set()
        slots=self.credit_plan.max_actor_acks_total-len(self._acks)
        for due,identity,actor,record in items:
            if actor in blocked_actors:
                self._policy_blocked_ids.add(identity)
                continue
            new_credit=self._balance[actor]+record.response
            if (len(allowed)>=slots or
                abs(new_credit)>self.credit_plan.max_abs_credit):
                blocked_actors.add(actor)
                self._policy_blocked_ids.add(identity)
                continue
            allowed.append((due,identity,actor,record))
        return allowed

    def _commit_ack(self,grant):
        identity=grant.judgment_id
        matches=[j for j in self.port.judgments if j.identity==identity]
        guard(len(matches)==1 and identity not in self._acked_ids and
              len(self._acks)<self.credit_plan.max_actor_acks_total and
              identity in self._consumed and identity in self.port._delivered_ids,
              'v2l replay/forged or unserviced actor credit transaction')
        record=matches[0]
        emission=self.port.emissions.get(record.source_emission)
        guard(emission is not None and emission.sender==grant.actor and
              emission.receiver==grant.issuer==record.issuer and
              grant.actor==record.recipient and
              grant.owner_pe==self._owners[grant.actor] and
              grant.response==record.response and
              grant.source_emission==record.source_emission and
              record.response in (-1,1) and
              record.created_tick>=self.port.ingress_ticks.get(
                  record.source_emission,10**9) and
              record.created_tick<record.due_tick<=grant.tick and
              record in self.port.mailbox(grant.actor),
              'v2l actor resource grant lacks delivered semantic causal custody')
        balance=self._balance[grant.actor]
        next_balance=balance+record.response
        last=self._actor_last_order.get(grant.actor)
        order=(record.due_tick,record.identity)
        guard(abs(next_balance)<=self.credit_plan.max_abs_credit and
              (last is None or order>last) and
              grant.phase in ('native-slack','post-native-tail'),
              'v2l credit bound or strict actor FIFO violated')
        ack=ActorCreditAckV2l(
            actor=grant.actor,owner_pe=grant.owner_pe,
            seq=self._actor_seq[grant.actor]+1,judgment_id=identity,
            source_emission=record.source_emission,
            receiver_issuer=record.issuer,decision=record.decision,
            response=record.response,created_tick=record.created_tick,
            due_tick=record.due_tick,serviced_tick=grant.tick,
            resource_phase=grant.phase,credit_before=balance,
            credit_after=next_balance,
            chain_prev=self._actor_roots[grant.actor],chain_digest='')
        ack=replace(ack,chain_digest=_digest_ack(ack))
        self._balance[grant.actor]=next_balance
        self._actor_seq[grant.actor]=ack.seq
        self._actor_last_order[grant.actor]=order
        self._actor_roots[grant.actor]=ack.chain_digest
        self._acked_ids.add(identity)
        self._acks.append(ack)

    def _service_tick(self,*args,**kwargs):
        start=len(self._grants)
        super()._service_tick(*args,**kwargs)
        for grant in self._grants[start:]:
            self._commit_ack(grant)

    def close_after_native(self,last_native_tick):
        """Avoid fabricated idle tail ticks after terminal policy refusal.

        Transport still drains causally; events not yet due retain time to
        mature. Once every due delivered event is permanently excluded by
        credit policy, no artificial service tick is added.
        """
        guard(not self._closed and self._bound and
              type(last_native_tick) is int and
              self._last_tick==last_native_tick and self._caps is not None,
              'v2l derived admission cannot close before native ticks')
        self.port.close()
        pe_caps,mem_pe_caps,dom_caps,pe_budget,mem_budget=self._caps
        for i in range(1,self.plan.max_tail_ticks+1):
            tick=last_native_tick+i
            eligible=self._pending(tick)
            future=any(record.identity not in self._consumed and
                       record.due_tick>tick
                       for actor in self._actors
                       for record in self.port.mailbox(actor))
            if not eligible and not future:
                break
            self._service_tick(tick,'post-native-tail',Counter(),0,
                Counter(),Counter(),0,pe_caps,mem_pe_caps,dom_caps,
                pe_budget,mem_budget)
            self._tail_ticks+=1
        self._closed=True

    def finish(self,next_native_tick,resource_timeline):
        """v2k counter/tail projection with v2l's terminal policy handling."""
        guard(not self._finished and type(next_native_tick) is int and
              type(resource_timeline) is list and bool(resource_timeline) and
              resource_timeline[-1]['tick']==next_native_tick-1 and
              len(resource_timeline)==len(self._native_baselines),
              'v2l actor credit finish lacks source-backed native resource rows')
        self._original_native_rows=len(resource_timeline)
        self.close_after_native(next_native_tick-1)
        for row in self._timeline:
            if row['phase']=='post-native-tail':
                resource_timeline.append(_tail_resource_row(row))
                self._synthetic_tail_rows+=1
        guard(self._synthetic_tail_rows==self._tail_ticks and
              len(resource_timeline)==self._original_native_rows+
                  self._synthetic_tail_rows,
              'v2l admitted control-only tail row custody mismatch')
        self._finished=True

    def audit_credit(self):
        guard(self._finished and self._closed and
              len(self._acks)==len(self._grants)==len(self._acked_ids) and
              [a.judgment_id for a in self._acks]==
                  [g.judgment_id for g in self._grants],
              'v2l actor credit journal/resource grant cardinality mismatch')
        roots={a:ZERO_ROOT for a in self._actors}
        balances={a:0 for a in self._actors}
        counts={a:0 for a in self._actors}
        last={}
        for grant,ack in zip(self._grants,self._acks):
            actor=grant.actor
            new=balances[actor]+grant.response
            order=(ack.due_tick,ack.judgment_id)
            guard(ack.actor==actor and ack.owner_pe==grant.owner_pe and
                  ack.judgment_id==grant.judgment_id and
                  ack.source_emission==grant.source_emission and
                  ack.receiver_issuer==grant.issuer and
                  ack.serviced_tick==grant.tick and
                  ack.resource_phase==grant.phase and
                  ack.response==grant.response and
                  ack.seq==counts[actor]+1 and
                  ack.credit_before==balances[actor] and
                  ack.credit_after==new and
                  abs(new)<=self.credit_plan.max_abs_credit and
                  ack.chain_prev==roots[actor] and
                  ack.chain_digest==_digest_ack(ack) and
                  (actor not in last or order>last[actor]),
                  'v2l unaccounted, out-of-order or altered actor ack')
            roots[actor]=ack.chain_digest
            balances[actor]=new
            counts[actor]+=1
            last[actor]=order
        guard(roots==self._actor_roots and balances==self._balance and
              counts==self._actor_seq and
              last==self._actor_last_order and
              self._acked_ids=={a.judgment_id for a in self._acks},
              'v2l actor credit register and journal chain diverged')
        return True

    def project_original_native_result(self,derived_result):
        self.audit_credit()
        return super().project_original_native_result(derived_result)

    def credit_journal(self):
        self.audit_credit()
        return [asdict(ack) for ack in self._acks]

    def summary(self):
        self.audit_credit()
        base=super().summary()
        guard(base['credit_by_actor']==self._balance and
              base['derived_resource_grants_committed']==len(self._acks),
              'v2l actor register credit differs from committed grants')
        pending={record.identity for actor in self._actors
                 for record in self.port.mailbox(actor)}-self._acked_ids
        blocked=pending & self._policy_blocked_ids
        return {
            **base,'schema':PROTOCOL_SCHEMA,
            'derived_actor_credit_ack_count':len(self._acks),
            'actor_credit_register':dict(sorted(self._balance.items())),
            'actor_credit_event_epochs':dict(sorted(self._actor_seq.items())),
            'actor_credit_chain_roots':dict(sorted(self._actor_roots.items())),
            'delivered_policy_blocked_pending':len(blocked),
            'delivered_other_unconsumed_pending':len(pending-blocked),
            'strict_actor_fifo_enforced':True,
            'exactly_once_derived_credit_journal':True,
            'credit_bounds_held':all(abs(n)<=self.credit_plan.max_abs_credit
                                     for n in self._balance.values()),
            'frozen_actor_state_changed':False,
            'frozen_actor_credit_contract_proven':False,
            'transport_silence_is_negative_evidence':False,
        }


def derive_actor_credit_executor(source:bytes,original,
                                 port:ReceiverPortV2h,
                                 credit:DerivedActorCreditProtocolV2l,
                                 observer:CallsiteObserver):
    """Recompile pinned frozen source in a separate, non-native namespace."""
    guard(type(port) is ReceiverPortV2h and
          type(credit) is DerivedActorCreditProtocolV2l and
          credit.port is port and type(observer) is CallsiteObserver and
          isinstance(original,FunctionType) and
          original.__name__=='execute_live_v0e',
          'v2l invalid source-derived actor credit compiler controls')
    node,callsites=audited_function(source)
    instrument=_IntegratedAdmissionInstrument()
    transformed=instrument.visit(node)
    guard(instrument.inline==[INLINE_ANCHOR] and
          instrument.finish==[FINISH_ANCHOR],
          'v2l frozen resource or tail anchor drift')
    ast.fix_missing_locations(transformed)
    semantic=_PortInstrument()
    transformed=semantic.visit(transformed)
    guard(tuple(sorted(semantic.found))==tuple(sorted(ANCHORS)),
          'v2l native source causal/receiver anchors changed')
    callsite=_Instrument()
    transformed=callsite.visit(transformed)
    guard(callsite.count==len(EXPECTED_CALLS),
          'v2l inherited native callsite inventory changed')
    module=ast.Module(body=[ast.ImportFrom(module='__future__',
        names=[ast.alias(name='annotations')],level=0),transformed],type_ignores=[])
    ast.fix_missing_locations(module)
    namespace=dict(original.__globals__)
    native_admit=namespace['_admit']

    def admit_and_bind(*args,**kwargs):
        result=native_admit(*args,**kwargs)
        guard(type(result) is tuple and len(result)==2,
              'v2l frozen actor admission return contract drift')
        credit.bind_admitted_actors(*result)
        return result

    def wrap(name,line,callee):
        guard(callable(callee),'v2l noncallable pinned callee')
        def inner(*args,**kwargs):
            try:
                result=callee(*args,**kwargs)
            except BaseException:
                observer.emit(name,line,False)
                raise
            observer.emit(name,line,True)
            return result
        return inner

    namespace['_admit']=admit_and_bind
    namespace['__v2h_port']=port
    namespace['__v2k_admission']=credit
    namespace['__spk_v2g_wrap']=wrap
    exec(compile(module,'<spk-v2l-pinned-derived-actor-credit>','exec'),namespace)
    derived=namespace['execute_live_v0e']
    guard(derived is not original and
          derived.__code__.co_varnames[:7]==original.__code__.co_varnames[:7] and
          '__v2k_admission' not in original.__globals__,
          'v2l derived compilation contaminated frozen native namespace')
    return (derived,callsites,tuple(sorted(semantic.found)),
            tuple(instrument.inline+instrument.finish))
