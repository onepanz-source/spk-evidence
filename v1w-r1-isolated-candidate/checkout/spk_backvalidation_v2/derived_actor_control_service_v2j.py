"""BV v2j: actor-addressed control service on a shadow, bounded PE ledger.

The service is invoked after the pinned native tick's final resource snapshot.
It reserves only remaining abstract PE and memory capacity for that tick.
It never alters native counters, actor states, forward computation or scheduler
output. After native termination a separately labelled research-only tail may
service still-pending controls. This is NOT native resource grant accounting.
"""
from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass
from types import FunctionType

from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver, EXPECTED_CALLS, _Instrument, audited_function, guard,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import (
    ANCHORS, ReceiverPortV2h, _PortInstrument,
)

SERVICE_SCHEMA = 'spk-bv-bounded-shadow-actor-control-service/research-v2j'
SERVICE_ANCHOR = 296
MAX_TAIL = 128


@dataclass(frozen=True, slots=True)
class ShadowServicePlanV2j:
    max_per_tick: int = 2
    per_actor_per_tick: int = 1
    max_tail_ticks: int = 32
    max_total_receipts: int = 512


@dataclass(frozen=True, slots=True)
class ShadowServiceGrantV2j:
    tick: int
    phase: str
    actor: str
    owner_pe: str
    judgment_id: str
    source_emission: str
    issuer: str
    response: int


class ActorControlServiceV2j:
    """Research-only service reservations, with strict native-slack budget.

    Each consumed packet charges one abstract service slot and two abstract
    local memory units (one O, one E), solely to a parallel shadow ledger.
    The frozen scheduler's counters are observed but never mutated.
    """

    def __init__(self, port: ReceiverPortV2h,
                 plan: ShadowServicePlanV2j = ShadowServicePlanV2j()):
        guard(type(port) is ReceiverPortV2h and
              type(plan) is ShadowServicePlanV2j and
              all(type(v) is int for v in (
                  plan.max_per_tick, plan.per_actor_per_tick,
                  plan.max_tail_ticks, plan.max_total_receipts)) and
              1 <= plan.max_per_tick <= 16 and
              1 <= plan.per_actor_per_tick <= plan.max_per_tick and
              0 <= plan.max_tail_ticks <= MAX_TAIL and
              1 <= plan.max_total_receipts <= 512,
              'invalid v2j shadow service plan')
        self.port, self.plan = port, plan
        self._owners: dict[str, str] = {}
        self._actors: dict[str, object] = {}
        self._bound = False
        self._consumed: set[str] = set()
        self._grants: list[ShadowServiceGrantV2j] = []
        self._timeline: list[dict] = []
        self._last_tick: int | None = None
        self._caps: tuple | None = None
        self._closed = False
        self._tail_ticks = 0
        self._pressure = Counter()

    def bind_admitted_actors(self, nodes, owners):
        guard(not self._bound and type(nodes) is dict and type(owners) is dict and
              set(nodes) == set(owners) and bool(nodes) and
              all(type(actor) is str and getattr(node,'node_id',None) == actor
                  for actor,node in nodes.items()) and
              all(type(pe) is str and bool(pe) for pe in owners.values()),
              'v2j actor ownership not supplied by native admission')
        self._actors = dict(nodes)
        self._owners = dict(owners)
        self._bound = True

    def _pending(self, tick):
        """Only receiver-issued, source-owned, delivered, due controls qualify."""
        candidates=[]
        for actor in sorted(self._actors):
            for record in self.port.mailbox(actor):
                if record.identity in self._consumed or record.due_tick > tick:
                    continue
                origin=self.port.emissions.get(record.source_emission)
                guard(origin is not None and origin.sender == actor and
                      origin.receiver == record.issuer and
                      record.recipient == actor and
                      record.identity in self.port._delivered_ids and
                      record in self.port.judgments and
                      record.created_tick < record.due_tick <= tick and
                      record.response in (-1,1),
                      'forged or premature v2j actor-owned control service')
                candidates.append((record.due_tick, record.identity, actor, record))
        return sorted(candidates)

    def _service_tick(self, tick, phase, service_used, pe_total,
                      mem_pe_used, mem_dom_used, mem_total,
                      pe_caps, mem_pe_caps, mem_domain_caps,
                      pe_budget, mem_budget):
        guard(self._bound and type(tick) is int and
              (self._last_tick is None or tick > self._last_tick) and
              phase in ('native-slack','post-native-tail') and
              type(pe_total) is int and type(mem_total) is int and
              type(pe_budget) is int and type(mem_budget) is int and
              0 <= pe_total <= pe_budget and 0 <= mem_total <= mem_budget and
              all(type(x) is dict or isinstance(x,Counter) for x in
                  (service_used,mem_pe_used,mem_dom_used,pe_caps,mem_pe_caps,
                   mem_domain_caps)),
              'v2j invalid native tick budget or nonmonotone service clock')
        self._last_tick=tick
        # Snapshot: research service NEVER mutates native accounting objects.
        used_pe=Counter(service_used)
        used_mem_pe=Counter(mem_pe_used)
        used_mem_dom=Counter(mem_dom_used)
        base=(pe_total,mem_total)
        receipts=[]
        per_actor=Counter()
        for _due,_id,actor,record in self._pending(tick):
            if len(self._grants)>=self.plan.max_total_receipts:
                self._pressure['total_receipts']+=1
                continue
            if len(receipts)>=self.plan.max_per_tick:
                self._pressure['per_tick']+=1
                continue
            if per_actor[actor]>=self.plan.per_actor_per_tick:
                self._pressure['per_actor']+=1
                continue
            pe=self._owners[actor]
            if used_pe[pe]+1 > pe_caps[pe] or pe_total+1 > pe_budget:
                self._pressure['service']+=1
                continue
            if (used_mem_pe[pe]+2 > mem_pe_caps[pe] or
                mem_total+2 > mem_budget or
                used_mem_dom['O']+1 > mem_domain_caps['O'] or
                used_mem_dom['E']+1 > mem_domain_caps['E']):
                self._pressure['memory']+=1
                continue
            pe_total+=1
            mem_total+=2
            used_pe[pe]+=1
            used_mem_pe[pe]+=2
            used_mem_dom['O']+=1
            used_mem_dom['E']+=1
            per_actor[actor]+=1
            self._consumed.add(record.identity)
            grant=ShadowServiceGrantV2j(tick,phase,actor,pe,
                record.identity,record.source_emission,record.issuer,record.response)
            self._grants.append(grant)
            receipts.append(grant)
        guard(pe_total<=pe_budget and mem_total<=mem_budget and
              all(used_pe[pe]<=limit for pe,limit in pe_caps.items()) and
              all(used_mem_pe[pe]<=limit for pe,limit in mem_pe_caps.items()) and
              all(used_mem_dom[d]<=limit for d,limit in mem_domain_caps.items()),
              'v2j shadow reservation oversubscribed frozen resource envelope')
        # Preserve a compact row for independent budget reconstruction.
        self._timeline.append({
            'tick':tick,'phase':phase,
            'native_service_used':base[0],
            'native_memory_used':base[1],
            'shadow_control_receipts':len(receipts),
            'shadow_service_units':len(receipts),
            'shadow_memory_units':2*len(receipts),
            'combined_service_used':pe_total,
            'combined_memory_used':mem_total,
            'service_budget':pe_budget,'memory_budget':mem_budget,
            'combined_service_by_pe':dict(sorted(used_pe.items())),
            'combined_memory_by_pe':dict(sorted(used_mem_pe.items())),
            'combined_memory_by_domain':dict(sorted(used_mem_dom.items())),
            'pe_service_caps':dict(sorted(pe_caps.items())),
            'pe_memory_caps':dict(sorted(mem_pe_caps.items())),
            'domain_memory_caps':dict(sorted(mem_domain_caps.items())),
        })

    def native_tick(self, tick, service_used, pe_total, mem_pe_used,
                    mem_dom_used, mem_total, owners, pe_caps, mem_pe_caps,
                    mem_domain_caps, pplan, mplan):
        guard(not self._closed and not self.port._closed and
              self._bound and owners == self._owners and
              self.port._clock == tick,
              'v2j shadow grant outside live pinned native tick')
        caps=(dict(pe_caps),dict(mem_pe_caps),dict(mem_domain_caps),
              pplan.fabric_slots_per_tick,mplan.fabric_slots_per_tick)
        if self._caps is None:
            self._caps=caps
        guard(self._caps == caps,'v2j native plan/capacity drift')
        self._service_tick(tick,'native-slack',service_used,pe_total,
            mem_pe_used,mem_dom_used,mem_total,*caps)

    def close_after_native(self, last_native_tick):
        guard(not self._closed and self._bound and
              type(last_native_tick) is int and
              self._last_tick == last_native_tick and self._caps is not None,
              'v2j service closure without audited native resource timeline')
        self.port.close()  # v2h research-only drain, never native actor intake
        pe_caps,mem_pe_caps,dom_caps,pe_budget,mem_budget=self._caps
        for i in range(1,self.plan.max_tail_ticks+1):
            if not self._pending(last_native_tick+i) and not any(
                    record.identity not in self._consumed
                    for actor in self._actors for record in self.port.mailbox(actor)):
                break
            self._service_tick(last_native_tick+i,'post-native-tail',
                Counter(),0,Counter(),Counter(),0,pe_caps,mem_pe_caps,
                dom_caps,pe_budget,mem_budget)
            self._tail_ticks+=1
        self._closed=True

    def grants(self):
        guard(self._closed,'v2j grants before service closure')
        return tuple(self._grants)

    def audit_native_timeline(self, native_timeline):
        guard(self._closed and type(native_timeline) is list,
              'v2j resource audit requires completed native result')
        live=[r for r in self._timeline if r['phase']=='native-slack']
        guard(len(live)==len(native_timeline) and
              all(r['tick']==n['tick'] and
                  r['native_service_used']==n['pe_service_total'] and
                  r['native_memory_used']==n['memory_total'] and
                  r['shadow_control_receipts']>=0 and
                  r['shadow_memory_units']==2*r['shadow_control_receipts']
                  for r,n in zip(live,native_timeline)),
              'v2j audited native timeline differs from pinned native result')
        return True

    def resource_timeline(self):
        guard(self._closed,'v2j resource timeline before service closure')
        return [dict(row) for row in self._timeline]

    def summary(self):
        guard(self._closed and self.port._closed,
              'v2j summary before native and control closure')
        delivered=self.port.summary()['control_delivered']
        guard(len(self._consumed)==len(self._grants) and
              len(self._grants)<=delivered and
              sum(row['shadow_control_receipts'] for row in self._timeline)==len(self._grants),
              'v2j shadow control service custody mismatch')
        live=sum(g.phase=='native-slack' for g in self._grants)
        tail=len(self._grants)-live
        return {
            'schema':SERVICE_SCHEMA,
            'admitted_actors':sorted(self._actors),
            'native_tick_resource_rows':sum(r['phase']=='native-slack'
                                            for r in self._timeline),
            'shadow_control_service_grants':len(self._grants),
            'native_slack_actor_service_grants':live,
            'post_native_shadow_tail_grants':tail,
            'tail_ticks':self._tail_ticks,
            'unconsumed_delivered_controls':delivered-len(self._grants),
            'delivered_controls':delivered,
            'shadow_pe_service_units':len(self._grants),
            'shadow_memory_units':2*len(self._grants),
            'credit_by_actor':{actor:sum(g.response for g in self._grants
                                          if g.actor==actor)
                               for actor in sorted(self._actors)},
            'shadow_pressure':dict(sorted(self._pressure.items())),
            'all_shadow_grants_within_native_plan_envelope':all(
                r['combined_service_used']<=r['service_budget'] and
                r['combined_memory_used']<=r['memory_budget'] and
                all(r['combined_service_by_pe'].get(pe,0)<=cap for pe,cap in
                    r['pe_service_caps'].items()) and
                all(r['combined_memory_by_pe'].get(pe,0)<=cap for pe,cap in
                    r['pe_memory_caps'].items()) and
                all(r['combined_memory_by_domain'].get(dom,0)<=cap for dom,cap in
                    r['domain_memory_caps'].items())
                for r in self._timeline),
            'absence_certificates':0,
            'frozen_actor_intake_observed':False,
            'frozen_native_resource_counters_mutated':False,
            'native_control_service_resources_accounted':False,
            'native_operator_updates':0,
            'native_learning_proven':False,
        }


class _ShadowTickInstrument(ast.NodeTransformer):
    def __init__(self):
        self.seen=[]

    def visit_Expr(self,node):
        self.generic_visit(node)
        if node.lineno != SERVICE_ANCHOR:
            return node
        guard(isinstance(node.value,ast.Call) and
              isinstance(node.value.func,ast.Attribute) and
              isinstance(node.value.func.value,ast.Name) and
              node.value.func.value.id == 'resource_timeline' and
              node.value.func.attr == 'append',
              'v2j native resource timeline hook shape drift')
        self.seen.append(node.lineno)
        names=('now','service_used','pe_total','mem_pe_used','mem_dom_used',
               'mem_total','owners','pe_caps','mem_pe_caps','mem_domain_caps',
               'pplan','mplan')
        hook=ast.Expr(value=ast.Call(
            func=ast.Attribute(value=ast.Name(id='__v2j_service',ctx=ast.Load()),
                               attr='native_tick',ctx=ast.Load()),
            args=[ast.Name(id=x,ctx=ast.Load()) for x in names],keywords=[]))
        return [node,hook]


def derive_shadow_service_executor(source:bytes, original,
                                   port:ReceiverPortV2h,
                                   service:ActorControlServiceV2j,
                                   observer:CallsiteObserver):
    """Pin the frozen AST and install a *separate* after-native-tick service."""
    guard(type(port) is ReceiverPortV2h and type(service) is ActorControlServiceV2j and
          service.port is port and type(observer) is CallsiteObserver and
          isinstance(original,FunctionType) and
          original.__name__=='execute_live_v0e',
          'invalid v2j native-derived hook controls')
    node,callsites=audited_function(source)
    tick_hook=_ShadowTickInstrument()
    transformed=tick_hook.visit(node)
    guard(tick_hook.seen==[SERVICE_ANCHOR],
          'v2j missing pinned native resource tick anchor')
    ast.fix_missing_locations(transformed)
    semantic=_PortInstrument()
    transformed=semantic.visit(transformed)
    guard(tuple(sorted(semantic.found))==tuple(sorted(ANCHORS)),
          'v2j inherited actor semantic anchors changed')
    callsite=_Instrument()
    transformed=callsite.visit(transformed)
    guard(callsite.count==len(EXPECTED_CALLS),
          'v2j inherited native callsite inventory changed')
    module=ast.Module(body=[ast.ImportFrom(module='__future__',
               names=[ast.alias(name='annotations')],level=0),transformed],
               type_ignores=[])
    ast.fix_missing_locations(module)
    isolated=dict(original.__globals__)
    native_admit=isolated['_admit']

    def admit_and_bind(*args,**kwargs):
        result=native_admit(*args,**kwargs)
        guard(type(result) is tuple and len(result)==2,
              'v2j native actor admission result changed')
        service.bind_admitted_actors(*result)
        return result

    def wrap(name,line,callee):
        guard(callable(callee),'v2j noncallable pinned callee')
        def inner(*args,**kwargs):
            try:
                result=callee(*args,**kwargs)
            except BaseException:
                observer.emit(name,line,False)
                raise
            observer.emit(name,line,True)
            return result
        return inner

    isolated['_admit']=admit_and_bind
    isolated['__v2h_port']=port
    isolated['__v2j_service']=service
    isolated['__spk_v2g_wrap']=wrap
    exec(compile(module,'<spk-v2j-pinned-derived-shadow-service>','exec'),isolated)
    derived=isolated['execute_live_v0e']
    guard(derived is not original and
          derived.__code__.co_varnames[:7] == original.__code__.co_varnames[:7] and
          '__v2j_service' not in original.__globals__,
          'v2j derived executor contaminated frozen runtime')
    return derived,callsites,tuple(sorted(semantic.found)),tick_hook.seen[0]
