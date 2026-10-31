"""BV v2q: independently charge actor credit *application* to derived PE/RAM.

Every v2q applied credit reserves one further PE service unit and two further
memory units (one O, one E) after the v2l resource-charged ACK. The grant
commits to the separate compiled derived scheduler's counters. The frozen
native and the preceding v2p ACK journal remain untouched. An exact inverse
projection strips only audited v2q grants, then delegates v2p/v2k projection.
"""
from __future__ import annotations

import ast
from collections import Counter
from copy import deepcopy
from dataclasses import asdict,dataclass,replace
from hashlib import sha256
import json
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
    _IntegratedAdmissionInstrument,INLINE_ANCHOR,FINISH_ANCHOR,SNAPSHOT_KEYS,
)
from spk_backvalidation_v2.derived_actor_priority_v2m import PRE_FORWARD_ANCHOR
from spk_backvalidation_v2.derived_causal_admission_v2o import (
    CausalAdmissionPlanV2o,DerivedCausalAdmissionV2o,
    _NativeCausalPreForwardInstrument,
)
from spk_backvalidation_v2.derived_actor_consumer_v2p import (
    ActorConsumerPlanV2p,DerivedActorConsumerV2p,
)

RESOURCE_CONSUMER_SCHEMA='spk-bv-derived-independent-actor-consumer-resource-charge/research-v2q'


@dataclass(frozen=True,slots=True)
class ConsumerResourcePlanV2q:
    max_consumer_service_per_tick: int = 1
    max_total_consumer_charges: int = 512
    max_resource_tail_ticks: int = 32
    max_consumer_memory_per_tick: int = 32


@dataclass(frozen=True,slots=True)
class ConsumerResourceChargeV2q:
    actor: str
    owner_pe: str
    ack_digest: str
    consumer_receipt_digest: str
    resource_tick: int
    resource_phase: str
    pe_service_units: int
    memory_units: int
    memory_domain_O: int
    memory_domain_E: int
    prior_charge_digest: str
    charge_digest: str


def _resource_charge_digest(charge):
    return sha256(json.dumps(asdict(replace(charge,charge_digest='')),
                ensure_ascii=True,sort_keys=True,
                separators=(',',':')).encode('utf8')).hexdigest()


def _snap(pe,used,mem,mem_pe,mem_domains):
    return {'pe_service_total':pe,
            'pe_service_by_pe':dict(sorted(used.items())),
            'memory_total':mem,
            'memory_by_pe':dict(sorted(mem_pe.items())),
            'memory_by_domain':dict(sorted(mem_domains.items()))}


def _budget_tail_row(row):
    return {
        'tick':row['tick'],'forward_computations':0,'feedback_sends':0,
        **row['after'],
        'link_total':0,'link_by_direction':[],
        'cross_inflight_end_tick':0,
    }


class DerivedActorResourceConsumerV2q(DerivedActorConsumerV2p):
    """v2p FIFO receipts gated by separately booked, source-capped resources."""

    def __init__(self,port:ReceiverPortV2h,*,
                 resource_plan:ConsumerResourcePlanV2q=ConsumerResourcePlanV2q(),
                 consumer_plan:ActorConsumerPlanV2p=ActorConsumerPlanV2p(),
                 admission_plan:CausalAdmissionPlanV2o=CausalAdmissionPlanV2o(),
                 credit_plan:ActorCreditPlanV2l=ActorCreditPlanV2l(),
                 service_plan:ShadowServicePlanV2j=ShadowServicePlanV2j()):
        guard(type(resource_plan) is ConsumerResourcePlanV2q and
              all(type(value) is int for value in (
                  resource_plan.max_consumer_service_per_tick,
                  resource_plan.max_total_consumer_charges,
                  resource_plan.max_resource_tail_ticks,
                  resource_plan.max_consumer_memory_per_tick)) and
              0<=resource_plan.max_consumer_service_per_tick<=16 and
              0<=resource_plan.max_total_consumer_charges<=512 and
              0<=resource_plan.max_resource_tail_ticks<=128 and
              0<=resource_plan.max_consumer_memory_per_tick<=32,
              'v2q invalid independent derived actor resource policy')
        super().__init__(port,consumer_plan=consumer_plan,
                         admission_plan=admission_plan,credit_plan=credit_plan,
                         service_plan=service_plan)
        self.resource_plan=resource_plan
        self._consumer_resource_charges=[]
        self._resource_charge_root=ZERO_ROOT
        self._resource_charge_trace=[]
        self._v2q_added_tail=[]
        self._v2q_native_charge_delta={}
        self._v2q_resource_tail_rows=0

    def _charge_tick(self,tick,phase,used,pe,mem_pe,domains,mem,
                     pe_caps,mem_pe_caps,domain_caps,pe_budget,mem_budget):
        guard(phase in ('after-native-forward','derived-consumer-tail') and
              type(tick) is int and type(pe) is int and type(mem) is int and
              all(isinstance(x,Counter) for x in (used,mem_pe,domains)) and
              all(type(x) is dict for x in
                  (pe_caps,mem_pe_caps,domain_caps)) and
              type(pe_budget) is int and type(mem_budget) is int and
              0<=pe<=pe_budget and 0<=mem<=mem_budget,
              'v2q invalid independently budgeted consumer service input')
        before=_snap(pe,used,mem,mem_pe,domains)
        available=min(self.consumer_plan.max_consume_per_tick,
                      self.consumer_plan.max_total_consume-len(self._consume_journal),
                      self.resource_plan.max_consumer_service_per_tick,
                      self.resource_plan.max_total_consumer_charges-
                          len(self._consumer_resource_charges),
                      self.resource_plan.max_consumer_memory_per_tick//2)
        prepared=[]
        rejection=None
        for ack in self._acks[len(self._consume_journal):]:
            if len(prepared)>=available:
                rejection='quota-or-throughput'
                break
            if ack.serviced_tick>tick:
                rejection='not-causally-serviced'
                break
            guard(ack.actor in self._owners and
                  ack.owner_pe==self._owners[ack.actor],
                  'v2q forged ACK resource owner custody')
            owner=ack.owner_pe
            if used[owner]+1>pe_caps[owner] or pe+1>pe_budget:
                rejection='independent-PE-capacity'
                break
            if (mem_pe[owner]+2>mem_pe_caps[owner] or
                mem+2>mem_budget or
                domains['O']+1>domain_caps['O'] or
                domains['E']+1>domain_caps['E']):
                rejection='independent-memory-capacity'
                break
            used[owner]+=1
            pe+=1
            mem_pe[owner]+=2
            mem+=2
            domains['O']+=1
            domains['E']+=1
            prepared.append(ack)
        # Reuse v2p's source/owner/FIFO/digest/epoch receipt constructor, but
        # admit only the number with a *separate* viable resource charge.
        original_plan=self.consumer_plan
        self.consumer_plan=replace(original_plan,
                                   max_consume_per_tick=len(prepared))
        start=len(self._consume_journal)
        try:
            DerivedActorConsumerV2p._consume_tick(self,tick,phase)
        finally:
            self.consumer_plan=original_plan
        applied=self._consume_journal[start:]
        guard(len(applied)==len(prepared) and
              [r.ack_digest for r in applied]==[a.chain_digest for a in prepared],
              'v2q derived ACK consumer differs from independent paid PE grants')
        for receipt in applied:
            charge=ConsumerResourceChargeV2q(
                actor=receipt.actor,owner_pe=receipt.owner_pe,
                ack_digest=receipt.ack_digest,
                consumer_receipt_digest=receipt.chain_digest,
                resource_tick=tick,resource_phase=phase,
                pe_service_units=1,memory_units=2,
                memory_domain_O=1,memory_domain_E=1,
                prior_charge_digest=self._resource_charge_root,charge_digest='')
            charge=replace(charge,charge_digest=_resource_charge_digest(charge))
            self._consumer_resource_charges.append(charge)
            self._resource_charge_root=charge.charge_digest
        after=_snap(pe,used,mem,mem_pe,domains)
        guard(pe<=pe_budget and mem<=mem_budget and
              all(used.get(owner,0)<=cap for owner,cap in pe_caps.items()) and
              all(mem_pe.get(owner,0)<=cap for owner,cap in mem_pe_caps.items()) and
              all(domains.get(domain,0)<=cap for domain,cap in domain_caps.items()),
              'v2q independent consumer counter exceeds source budget')
        self._resource_charge_trace.append({
            'tick':tick,'phase':phase,'before':before,'after':after,
            'grants':len(prepared),'reject_reason':rejection,
            'source_PE_budget':pe_budget,'source_memory_budget':mem_budget,
            'source_PE_caps':dict(sorted(pe_caps.items())),
            'source_memory_PE_caps':dict(sorted(mem_pe_caps.items())),
            'source_memory_domain_caps':dict(sorted(domain_caps.items())),
        })
        return pe,mem

    def admit_tick(self,tick,service_used,pe_total,mem_pe_used,
                   mem_dom_used,mem_total,owners,pe_caps,mem_pe_caps,
                   mem_domain_caps,pplan,mplan):
        pe_total,mem_total=DerivedCausalAdmissionV2o.admit_tick(
            self,tick,service_used,pe_total,mem_pe_used,mem_dom_used,mem_total,
            owners,pe_caps,mem_pe_caps,mem_domain_caps,pplan,mplan)
        pe_total,mem_total=self._charge_tick(tick,'after-native-forward',
            service_used,pe_total,mem_pe_used,mem_dom_used,mem_total,
            pe_caps,mem_pe_caps,mem_domain_caps,
            pplan.fabric_slots_per_tick,mplan.fabric_slots_per_tick)
        self._v2q_native_charge_delta[tick]=self._resource_charge_trace[-1]
        return pe_total,mem_total

    def finish(self,next_native_tick,resource_timeline):
        DerivedCausalAdmissionV2o.finish(self,next_native_tick,resource_timeline)
        caps=self._caps
        guard(caps is not None and self._finished,
              'v2q independent resource tail without source-closed ACK journal')
        pe_caps,mem_pe_caps,domain_caps,pe_budget,mem_budget=caps
        last_tick=resource_timeline[-1]['tick']
        for step in range(1,self.resource_plan.max_resource_tail_ticks+1):
            if (len(self._consume_journal)==len(self._acks) or
                len(self._consumer_resource_charges)>=
                    self.resource_plan.max_total_consumer_charges or
                len(self._consume_journal)>=self.consumer_plan.max_total_consume or
                self.consumer_plan.max_consume_per_tick==0 or
                self.resource_plan.max_consumer_service_per_tick==0 or
                self.resource_plan.max_consumer_memory_per_tick<2):
                break
            tick=last_tick+step
            used,mem_pe,domains=Counter(),Counter(),Counter()
            self._charge_tick(tick,'derived-consumer-tail',used,0,mem_pe,domains,0,
                pe_caps,mem_pe_caps,domain_caps,pe_budget,mem_budget)
            row=self._resource_charge_trace[-1]
            resource_timeline.append(_budget_tail_row(row))
            self._v2q_added_tail.append(_budget_tail_row(row))
            self._consumer_tail_ticks+=1
            self._v2q_resource_tail_rows+=1
        guard(self._v2q_resource_tail_rows==len(self._v2q_added_tail),
              'v2q consumer tail generation mismatched booked rows')

    def audit_resource_consumer(self):
        DerivedActorConsumerV2p.audit_consumer(self)
        guard(self._finished and
              len(self._consumer_resource_charges)==len(self._consume_journal) and
              len(self._resource_charge_trace)==len(self._consume_trace) and
              self._v2q_resource_tail_rows==self._consumer_tail_ticks and
              len(self._v2q_native_charge_delta)==self._original_native_rows,
              'v2q unaccounted independently charged consumer receipt or tick')
        root=ZERO_ROOT
        charges_by_tick={}
        for charge,receipt in zip(self._consumer_resource_charges,self._consume_journal):
            guard(charge.actor==receipt.actor and
                  charge.owner_pe==receipt.owner_pe==self._owners[receipt.actor] and
                  charge.ack_digest==receipt.ack_digest and
                  charge.consumer_receipt_digest==receipt.chain_digest and
                  charge.resource_tick==receipt.consume_tick and
                  charge.resource_phase==receipt.consume_phase and
                  charge.pe_service_units==1 and charge.memory_units==2 and
                  charge.memory_domain_O==charge.memory_domain_E==1 and
                  charge.prior_charge_digest==root and
                  charge.charge_digest==_resource_charge_digest(charge),
                  'v2q independent paid resource ownership/digest replay')
            root=charge.charge_digest
            charges_by_tick.setdefault(charge.resource_tick,[]).append(charge)
        guard(root==self._resource_charge_root,
              'v2q independent consumer resource chain root drift')
        pe_caps,mem_pe_caps,domain_caps,pe_budget,mem_budget=self._caps
        audited_consumed=0
        for row,virtual in zip(self._resource_charge_trace,self._consume_trace):
            before,after=row['before'],row['after']
            charges=charges_by_tick.get(row['tick'],[])
            guard(row['source_PE_budget']==pe_budget and
                  row['source_memory_budget']==mem_budget and
                  row['source_PE_caps']==dict(sorted(pe_caps.items())) and
                  row['source_memory_PE_caps']==
                      dict(sorted(mem_pe_caps.items())) and
                  row['source_memory_domain_caps']==
                      dict(sorted(domain_caps.items())),
                  'v2q altered source-authorized PE/memory budget envelope')
            pe=Counter(before['pe_service_by_pe'])
            mem=Counter(before['memory_by_pe'])
            domains=Counter(before['memory_by_domain'])
            preview_pe=Counter(pe)
            preview_mem=Counter(mem)
            preview_dom=Counter(domains)
            preview_total_pe=before['pe_service_total']
            preview_total_mem=before['memory_total']
            limit=min(self.consumer_plan.max_consume_per_tick,
                      self.consumer_plan.max_total_consume-audited_consumed,
                      self.resource_plan.max_consumer_service_per_tick,
                      self.resource_plan.max_total_consumer_charges-audited_consumed,
                      self.resource_plan.max_consumer_memory_per_tick//2)
            preview=[]
            expected_reason=None
            for ack in self._acks[audited_consumed:]:
                # Later ACKs were not yet in the mailbox at this live tick.
                if ack.serviced_tick>row['tick']:
                    break
                if len(preview)>=limit:
                    expected_reason='quota-or-throughput'
                    break
                owner=ack.owner_pe
                if (preview_pe[owner]+1>pe_caps[owner] or
                    preview_total_pe+1>pe_budget):
                    expected_reason='independent-PE-capacity'
                    break
                if (preview_mem[owner]+2>mem_pe_caps[owner] or
                    preview_total_mem+2>mem_budget or
                    preview_dom['O']+1>domain_caps['O'] or
                    preview_dom['E']+1>domain_caps['E']):
                    expected_reason='independent-memory-capacity'
                    break
                preview_pe[owner]+=1
                preview_total_pe+=1
                preview_mem[owner]+=2
                preview_total_mem+=2
                preview_dom['O']+=1
                preview_dom['E']+=1
                preview.append(ack)
            guard([a.chain_digest for a in preview]==
                  [c.ack_digest for c in charges] and
                  row['reject_reason']==expected_reason,
                  'v2q source FIFO service eligibility, pressure or quota forged')
            audited_consumed+=len(charges)
            for charge in charges:
                pe[charge.owner_pe]+=1
                mem[charge.owner_pe]+=2
                domains['O']+=1
                domains['E']+=1
            expected=_snap(before['pe_service_total']+len(charges),pe,
                           before['memory_total']+2*len(charges),mem,domains)
            guard(row['tick']==virtual['tick'] and
                  row['phase']==virtual['phase'] and
                  row['grants']==virtual['actor_consumer_applications']==
                      len(charges) and
                  expected==after and
                  after['pe_service_total']<=row['source_PE_budget'] and
                  after['memory_total']<=row['source_memory_budget'] and
                  all(after['pe_service_by_pe'].get(pe_id,0)<=cap
                      for pe_id,cap in row['source_PE_caps'].items()) and
                  all(after['memory_by_pe'].get(pe_id,0)<=cap
                      for pe_id,cap in row['source_memory_PE_caps'].items()) and
                  all(after['memory_by_domain'].get(domain,0)<=cap
                      for domain,cap in row['source_memory_domain_caps'].items()) and
                  row['grants']<=self.resource_plan.max_consumer_service_per_tick and
                  row['grants']*2<=self.resource_plan.max_consumer_memory_per_tick,
                  'v2q independent PE/memory budget or actor charge trace drift')
            if row['phase']=='after-native-forward':
                source=next(r for r in self._timeline if r['tick']==row['tick'])
                guard(before==_snap(source['combined_service_used'],
                    Counter(source['combined_service_by_pe']),
                    source['combined_memory_used'],
                    Counter(source['combined_memory_by_pe']),
                    Counter(source['combined_memory_by_domain'])),
                    'v2q inline charge precedes true v2l ACK service budget')
            else:
                guard(before==_snap(0,Counter(),0,Counter(),Counter()),
                      'v2q consumer-only tail hid forward or native resource spend')
        guard(len(self._consumer_resource_charges)<=
                  self.resource_plan.max_total_consumer_charges and
              audited_consumed==len(self._consumer_resource_charges),
              'v2q independent consumer total resource capacity exceeded')
        return True

    def project_original_native_result(self,derived_result):
        self.audit_resource_consumer()
        guard(type(derived_result) is dict and
              type(derived_result.get('resources')) is dict and
              type(derived_result['resources'].get('timeline')) is list and
              len(derived_result['resources']['timeline'])==
                  self._original_native_rows+self._synthetic_tail_rows+
                      self._v2q_resource_tail_rows,
              'v2q full derived result lacks separately paid consumer rows')
        projected=deepcopy(derived_result)
        rows=projected['resources']['timeline']
        guard(rows[-self._v2q_resource_tail_rows:]==self._v2q_added_tail
              if self._v2q_resource_tail_rows else True,
              'v2q forged or truncated extra consumer-only PE/memory rows')
        if self._v2q_resource_tail_rows:
            del rows[-self._v2q_resource_tail_rows:]
        for row in rows[:self._original_native_rows]:
            resource=self._v2q_native_charge_delta.get(row['tick'])
            guard(resource is not None and
                  all(row.get(key)==resource['after'][key] for key in SNAPSHOT_KEYS),
                  'v2q inline derived consumer PE/memory counter mutation')
            row.update(deepcopy(resource['before']))
        return DerivedActorConsumerV2p.project_original_native_result(
            self,projected)

    def resource_charge_journal(self):
        self.audit_resource_consumer()
        return [asdict(item) for item in self._consumer_resource_charges]

    def resource_charge_trace(self):
        self.audit_resource_consumer()
        return deepcopy(self._resource_charge_trace)

    def summary(self):
        original=DerivedActorConsumerV2p.summary(self)
        self.audit_resource_consumer()
        count=len(self._consumer_resource_charges)
        return {**original,
            'schema':RESOURCE_CONSUMER_SCHEMA,
            'consumer_consumption_borrows_existing_ACK_charge':False,
            'consumer_extra_PE_or_memory_budget_charged':True,
            'derived_independent_consumer_PE_units':count,
            'derived_independent_consumer_memory_units':2*count,
            'derived_independent_consumer_resource_charges':count,
            'consumer_independent_inline_charges':sum(
                x.resource_phase=='after-native-forward'
                for x in self._consumer_resource_charges),
            'consumer_independent_tail_charges':sum(
                x.resource_phase=='derived-consumer-tail'
                for x in self._consumer_resource_charges),
            'new_consumer_only_resource_timeline_rows':self._v2q_resource_tail_rows,
            'consumer_independent_resource_chain_root':self._resource_charge_root,
            'consumer_resource_capacity_rejections':sum(
                r['reject_reason'] in ('independent-PE-capacity',
                                       'independent-memory-capacity')
                for r in self._resource_charge_trace),
            'independent_consumer_source_budget_verified':True,
            'consumer_physical_hardware_cost_proven':False,
            'frozen_native_actor_consumer_changed':False,
        }


def derive_resource_consumer_executor(source:bytes,original,port:ReceiverPortV2h,
                                     consumer:DerivedActorResourceConsumerV2q,
                                     observer:CallsiteObserver):
    guard(type(port) is ReceiverPortV2h and
          type(consumer) is DerivedActorResourceConsumerV2q and
          consumer.port is port and type(observer) is CallsiteObserver and
          isinstance(original,FunctionType) and
          original.__name__=='execute_live_v0e',
          'v2q invalid source-backed independent consumer compiler controls')
    node,callsites=audited_function(source)
    priority=_NativeCausalPreForwardInstrument()
    transformed=priority.visit(node)
    guard(priority.found==[PRE_FORWARD_ANCHOR],
          'v2q pinned native-ready event arbitration hook drift')
    resources=_IntegratedAdmissionInstrument()
    transformed=resources.visit(transformed)
    guard(resources.inline==[INLINE_ANCHOR] and
          resources.finish==[FINISH_ANCHOR],
          'v2q pinned native resource/closure hook drift')
    ast.fix_missing_locations(transformed)
    semantic=_PortInstrument()
    transformed=semantic.visit(transformed)
    guard(tuple(sorted(semantic.found))==tuple(sorted(ANCHORS)),
          'v2q source-native receiver and actor semantic hook drift')
    callsite=_Instrument()
    transformed=callsite.visit(transformed)
    guard(callsite.count==len(EXPECTED_CALLS),
          'v2q audited source-native callsite drift')
    module=ast.Module(body=[ast.ImportFrom(module='__future__',
        names=[ast.alias(name='annotations')],level=0),transformed],type_ignores=[])
    ast.fix_missing_locations(module)
    namespace=dict(original.__globals__)
    native_admit=namespace['_admit']

    def bind_admit(*args,**kwargs):
        result=native_admit(*args,**kwargs)
        guard(type(result) is tuple and len(result)==2,
              'v2q source actor admission custody changed')
        consumer.bind_admitted_actors(*result)
        return result

    def wrap(name,line,callee_fn):
        guard(callable(callee_fn),'v2q source native audited callee not callable')
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
    exec(compile(module,'<spk-v2q-independent-consumer-resource>',
                 'exec'),namespace)
    derived=namespace['execute_live_v0e']
    guard(derived is not original and
          derived.__code__.co_varnames[:7]==original.__code__.co_varnames[:7] and
          '__v2o_causal_admission' not in original.__globals__ and
          '__v2k_admission' not in original.__globals__,
          'v2q separate derived compiler contaminated frozen scheduler')
    return derived,callsites,tuple(sorted(semantic.found)),(
        PRE_FORWARD_ANCHOR,INLINE_ANCHOR,FINISH_ANCHOR)
