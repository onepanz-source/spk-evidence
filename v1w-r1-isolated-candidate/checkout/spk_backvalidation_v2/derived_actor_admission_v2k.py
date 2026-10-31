"""BV v2k: commit actor-control grants to a *derived* scheduler's counters.

Unlike v2j's parallel shadow ledger, the separately compiled v2k executor
updates its own live `service_used`, `pe_total`, `mem_*` and resource timeline
after the original native work for the tick is finished. This changes the
DERIVED full result intentionally. A fail-closed projection must recover the
entire untouched frozen native result. No frozen source or native actor state
is changed; the cost and extra control-only ticks remain research choices.
"""
from __future__ import annotations

import ast
from collections import Counter
from copy import deepcopy
from types import FunctionType

from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver, EXPECTED_CALLS, _Instrument, audited_function, guard,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import (
    ANCHORS, ReceiverPortV2h, _PortInstrument,
)
from spk_backvalidation_v2.derived_actor_control_service_v2j import (
    ActorControlServiceV2j, ShadowServicePlanV2j,
)

ADMISSION_SCHEMA='spk-bv-derived-actor-control-resource-admission/research-v2k'
INLINE_ANCHOR=296
FINISH_ANCHOR=307
SNAPSHOT_KEYS=('pe_service_total','pe_service_by_pe','memory_total',
               'memory_by_pe','memory_by_domain')


def _tail_resource_row(row):
    return {
        'tick':row['tick'],'forward_computations':0,'feedback_sends':0,
        'pe_service_total':row['combined_service_used'],
        'pe_service_by_pe':dict(row['combined_service_by_pe']),
        'memory_total':row['combined_memory_used'],
        'memory_by_pe':dict(row['combined_memory_by_pe']),
        'memory_by_domain':dict(row['combined_memory_by_domain']),
        'link_total':0,'link_by_direction':[],
        'cross_inflight_end_tick':0,
    }


class DerivedActorAdmissionV2k(ActorControlServiceV2j):
    """Verified after-forward resource commit inside the derived scheduler.

    The v2j admission algorithm decides which receipts fit. v2k additionally
    books those exact grants into mutable DERIVED native-tick Counters, and
    produces separately budgeted control-only timeline rows after termination.
    """

    def __init__(self, port:ReceiverPortV2h,
                 plan:ShadowServicePlanV2j=ShadowServicePlanV2j()):
        super().__init__(port,plan)
        self._native_baselines:dict[int,dict]={}
        self._inline_grants:dict[int,tuple]={}
        self._original_native_rows=0
        self._synthetic_tail_rows=0
        self._finished=False

    def admit_tick(self, tick, service_used, pe_total, mem_pe_used,
                   mem_dom_used, mem_total, owners, pe_caps, mem_pe_caps,
                   mem_domain_caps, pplan, mplan):
        guard(not self._finished and type(service_used) is Counter and
              type(mem_pe_used) is Counter and type(mem_dom_used) is Counter and
              tick not in self._native_baselines,
              'v2k duplicate or unsafe native-derived resource counter grant')
        self._native_baselines[tick]={
            'pe_service_total':pe_total,
            'pe_service_by_pe':dict(sorted(service_used.items())),
            'memory_total':mem_total,
            'memory_by_pe':dict(sorted(mem_pe_used.items())),
            'memory_by_domain':dict(sorted(mem_dom_used.items())),
        }
        previous=len(self._grants)
        # Inherited proven capacity logic. It cannot write to passed Counters.
        super().native_tick(tick,service_used,pe_total,mem_pe_used,
            mem_dom_used,mem_total,owners,pe_caps,mem_pe_caps,mem_domain_caps,
            pplan,mplan)
        new=tuple(self._grants[previous:])
        guard(all(g.phase=='native-slack' and g.tick==tick for g in new),
              'v2k native-grant time/ownership mismatch')
        for grant in new:
            service_used[grant.owner_pe]+=1
            mem_pe_used[grant.owner_pe]+=2
            mem_dom_used['O']+=1
            mem_dom_used['E']+=1
            pe_total+=1
            mem_total+=2
        row=self._timeline[-1]
        guard(row['tick']==tick and
              pe_total==row['combined_service_used'] and
              mem_total==row['combined_memory_used'] and
              dict(sorted(service_used.items()))==row['combined_service_by_pe'] and
              dict(sorted(mem_pe_used.items()))==row['combined_memory_by_pe'] and
              dict(sorted(mem_dom_used.items()))==row['combined_memory_by_domain'],
              'v2k derived counter commit disagrees with admitted budget ledger')
        self._inline_grants[tick]=new
        return pe_total,mem_total

    def finish(self, next_native_tick, resource_timeline):
        guard(not self._finished and type(next_native_tick) is int and
              type(resource_timeline) is list and bool(resource_timeline) and
              resource_timeline[-1]['tick']==next_native_tick-1 and
              len(resource_timeline)==len(self._native_baselines),
              'v2k control-tail cannot start from unaudited native loop')
        self._original_native_rows=len(resource_timeline)
        super().close_after_native(next_native_tick-1)
        for row in self._timeline:
            if row['phase']!='post-native-tail':
                continue
            resource_timeline.append(_tail_resource_row(row))
            self._synthetic_tail_rows+=1
        guard(self._synthetic_tail_rows==self._tail_ticks and
              len(resource_timeline)==self._original_native_rows+
                  self._synthetic_tail_rows,
              'v2k synthetic control-only timeline cardinality drift')
        self._finished=True

    def project_original_native_result(self, derived_result):
        """Remove only precisely accounted research grants, reject other drift."""
        guard(self._finished and self._closed and
              type(derived_result) is dict and
              type(derived_result.get('resources')) is dict and
              type(derived_result['resources'].get('timeline')) is list and
              len(derived_result['resources']['timeline'])==
                  self._original_native_rows+self._synthetic_tail_rows,
              'v2k projection requires exact integrated result')
        projected=deepcopy(derived_result)
        rows=projected['resources']['timeline']
        expected_tail=[_tail_resource_row(row) for row in self._timeline
                       if row['phase']=='post-native-tail']
        guard(rows[self._original_native_rows:]==expected_tail,
              'v2k unaccounted post-native derived resource rows')
        for row in rows[:self._original_native_rows]:
            tick=row['tick']
            guard(tick in self._native_baselines and
                  tick in self._inline_grants,
                  'v2k projection missing native tick custody')
            baseline=self._native_baselines[tick]
            grants=self._inline_grants[tick]
            pe=Counter(baseline['pe_service_by_pe'])
            mem=Counter(baseline['memory_by_pe'])
            domains=Counter(baseline['memory_by_domain'])
            for g in grants:
                pe[g.owner_pe]+=1
                mem[g.owner_pe]+=2
                domains['O']+=1
                domains['E']+=1
            expected={
                'pe_service_total':baseline['pe_service_total']+len(grants),
                'pe_service_by_pe':dict(sorted(pe.items())),
                'memory_total':baseline['memory_total']+2*len(grants),
                'memory_by_pe':dict(sorted(mem.items())),
                'memory_by_domain':dict(sorted(domains.items())),
            }
            guard(all(row.get(key)==expected[key] for key in SNAPSHOT_KEYS),
                  'v2k unaccounted derived resource modification: refuse projection')
            row.update(deepcopy(baseline))
        del rows[self._original_native_rows:]
        guard([r['tick'] for r in rows]==list(self._native_baselines),
              'v2k projected native tick order mismatch')
        return projected

    def summary(self):
        guard(self._finished,'v2k summary before derived scheduler finish')
        inherited=super().summary()
        return {
            'schema':ADMISSION_SCHEMA,
            'derived_resource_grants_committed':inherited['shadow_control_service_grants'],
            'derived_inline_actor_grants':inherited['native_slack_actor_service_grants'],
            'derived_control_tail_grants':inherited['post_native_shadow_tail_grants'],
            'unconsumed_delivered_controls':inherited['unconsumed_delivered_controls'],
            'delivered_controls':inherited['delivered_controls'],
            'native_original_timeline_rows':self._original_native_rows,
            'new_derived_control_only_timeline_rows':self._synthetic_tail_rows,
            'derived_committed_pe_service_units':inherited['shadow_pe_service_units'],
            'derived_committed_memory_units':inherited['shadow_memory_units'],
            'credit_by_actor':inherited['credit_by_actor'],
            'resource_pressure':inherited['shadow_pressure'],
            'within_original_native_plan_capacity':
                inherited['all_shadow_grants_within_native_plan_envelope'],
            'absence_certificates':0,
            'derived_scheduler_resource_counters_intentionally_changed':True,
            'frozen_original_resource_counters_changed':False,
            'frozen_native_actor_intake_observed':False,
            'native_learning_proven':False,
            'native_operator_updates':0,
        }


class _IntegratedAdmissionInstrument(ast.NodeTransformer):
    def __init__(self):
        self.inline=[]
        self.finish=[]

    def visit_Expr(self,node):
        self.generic_visit(node)
        if node.lineno!=INLINE_ANCHOR:
            return node
        guard(isinstance(node.value,ast.Call) and
              isinstance(node.value.func,ast.Attribute) and
              isinstance(node.value.func.value,ast.Name) and
              node.value.func.value.id=='resource_timeline' and
              node.value.func.attr=='append',
              'v2k native resource counter hook shape changed')
        names=('now','service_used','pe_total','mem_pe_used','mem_dom_used',
               'mem_total','owners','pe_caps','mem_pe_caps','mem_domain_caps',
               'pplan','mplan')
        call=ast.Call(func=ast.Attribute(
            value=ast.Name(id='__v2k_admission',ctx=ast.Load()),
            attr='admit_tick',ctx=ast.Load()),
            args=[ast.Name(id=n,ctx=ast.Load()) for n in names],keywords=[])
        target=ast.Tuple(elts=[ast.Name(id=n,ctx=ast.Store())
                               for n in ('pe_total','mem_total')],ctx=ast.Store())
        assign=ast.Assign(targets=[target],value=call)
        self.inline.append(node.lineno)
        return [assign,node]

    def visit_FunctionDef(self,node):
        self.generic_visit(node)
        if node.name!='execute_live_v0e':
            return node
        positions=[i for i,statement in enumerate(node.body)
                   if isinstance(statement,ast.While) and statement.lineno==125]
        guard(len(positions)==1,'v2k native while boundary drift')
        index=positions[0]
        guard(index+1<len(node.body) and
              isinstance(node.body[index+1],ast.If) and
              node.body[index+1].lineno==FINISH_ANCHOR,
              'v2k post-native completion anchor drift')
        hook=ast.Expr(value=ast.Call(func=ast.Attribute(
            value=ast.Name(id='__v2k_admission',ctx=ast.Load()),
            attr='finish',ctx=ast.Load()),
            args=[ast.Name(id='now',ctx=ast.Load()),
                  ast.Name(id='resource_timeline',ctx=ast.Load())],keywords=[]))
        node.body.insert(index+1,hook)
        self.finish.append(node.body[index+2].lineno)
        return node


def derive_resource_admission_executor(source:bytes, original,
                                       port:ReceiverPortV2h,
                                       admission:DerivedActorAdmissionV2k,
                                       observer:CallsiteObserver):
    guard(type(port) is ReceiverPortV2h and
          type(admission) is DerivedActorAdmissionV2k and
          admission.port is port and type(observer) is CallsiteObserver and
          isinstance(original,FunctionType) and
          original.__name__=='execute_live_v0e',
          'v2k invalid derived integrated scheduler controls')
    node,callsites=audited_function(source)
    instrument=_IntegratedAdmissionInstrument()
    transformed=instrument.visit(node)
    guard(instrument.inline==[INLINE_ANCHOR] and
          instrument.finish==[FINISH_ANCHOR],
          'v2k native source resource/tail anchor mismatch')
    ast.fix_missing_locations(transformed)
    semantic=_PortInstrument()
    transformed=semantic.visit(transformed)
    guard(tuple(sorted(semantic.found))==tuple(sorted(ANCHORS)),
          'v2k inherited semantic source anchors changed')
    callsite=_Instrument()
    transformed=callsite.visit(transformed)
    guard(callsite.count==len(EXPECTED_CALLS),
          'v2k inherited native callsite roster drift')
    module=ast.Module(body=[ast.ImportFrom(module='__future__',
        names=[ast.alias(name='annotations')],level=0),transformed],type_ignores=[])
    ast.fix_missing_locations(module)
    namespace=dict(original.__globals__)
    native_admit=namespace['_admit']

    def admit_and_bind(*args,**kwargs):
        result=native_admit(*args,**kwargs)
        guard(type(result) is tuple and len(result)==2,
              'v2k native actor ownership result drift')
        admission.bind_admitted_actors(*result)
        return result

    def wrap(name,line,callee):
        guard(callable(callee),'v2k noncallable pinned callee')
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
    namespace['__v2k_admission']=admission
    namespace['__spk_v2g_wrap']=wrap
    exec(compile(module,'<spk-v2k-pinned-derived-counter-commit>','exec'),namespace)
    derived=namespace['execute_live_v0e']
    guard(derived is not original and
          derived.__code__.co_varnames[:7]==original.__code__.co_varnames[:7] and
          '__v2k_admission' not in original.__globals__,
          'v2k derived counter program contaminated frozen source')
    return (derived,callsites,tuple(sorted(semantic.found)),
            tuple(instrument.inline+instrument.finish))
