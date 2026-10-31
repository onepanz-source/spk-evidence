"""New bounded three-choice corpus: typed original A1 objects and genuine frozen PE.

An original PE A program explicitly encodes a goal and compares incoming
channel identity via the local ACC/CMP/EMIT/RESET algebra. The host supplies
the goal and world. No claim of independently chosen goals or N-node support.
"""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
from spk_native_learning_v1.conformance_v1 import pin_sources as _pin_original
from spk_native_learning_v1.generalized_scheduler_v1t import CHOICES_V1T

GOAL_CHANNELS={11:(1,13,3),12:(2,14,4),15:(5,16,6)}

def pin_sources(root):
    pins=_pin_original(root)
    from spk_native_learning_v1 import generalized_scheduler_v1t as r
    from spk_architecture_v1 import pe_execution_v1b as original
    if r._compute_local is not original._compute_local or r._admit is not original._admit:
        raise AssertionError('GENUINE_FROZEN_PE_NOT_EXECUTED')
    return pins

def build_case(choice,goal,*, second_tick=30):
    if type(choice) is not int or choice not in CHOICES_V1T:
        raise ValueError('INVALID_THREE_CHOICE_INITIAL')
    if type(goal) is not int or goal not in CHOICES_V1T:
        raise ValueError('INVALID_THREE_CHOICE_GOAL')
    if type(second_tick) is not int or second_tick<20 or second_tick>165:
        raise ValueError('INVALID_SECOND_TICK')
    # Reuse original typed case constructors; original T7 remains unmodified.
    from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import case_for
    case=case_for(11,11)
    nodes={n.node_id:n for n in case.nodes}
    cprog=(('ACC',(1,1)),('CMP',1),('EMIT',choice),('RESET',0))
    bprog=[]; aprog=[]
    for candidate,(in_b,out_b,in_a) in GOAL_CHANNELS.items():
        bprog.extend([('ACC',(1,in_b)),('CMP',1),('EMIT',out_b),('RESET',0)])
        aprog.extend([('ACC',(1,in_a)),('CMP',1),('EMIT',21 if candidate==goal else 22),('EMIT',7),('RESET',0)])
    programs={'C':cprog,'B':tuple(bprog),'A':tuple(aprog)}
    rewritten=tuple(replace(n,instructions=programs[n.node_id],initial_raw=0) for n in case.nodes)
    prototype=case.edges[0]
    connections=[]
    for choice_i,(in_b,out_b,in_a) in GOAL_CHANNELS.items():
        connections.extend([('C',choice_i,'B',in_b),('B',out_b,'A',in_a)])
    edges=tuple(replace(prototype,source_node=u,source_channel=out,
                        target_node=v,target_channel=inp,delay_ticks=1)
                for u,out,v,inp in connections)
    inp=case.events[0]
    events=tuple(replace(inp,timestamp=t,node_id='C',channel=1)
                 for t in (10,second_tick,second_tick+20,second_tick+40))
    return replace(case,nodes=rewritten,edges=edges,events=events)

def setup(choice,goal,*,second_tick=30):
    from spk_architecture_v1.pe_fabric_v1a import plan_v1a
    from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
    from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
    from spk_architecture_v1.causal_memory_v1c import uniform_causal_memory_plan_v1c
    from spk_architecture_v1.causal_transport_v1d import CausalLinkPlanV1d
    case=build_case(choice,goal,second_tick=second_tick)
    fabric=plan_v1a(case,'spread')
    return (case,fabric,TransportPlanV1a(0,16),
      uniform_causal_service_plan_v1b(fabric,pe_slots=3,fabric_slots_per_tick=4),
      uniform_causal_memory_plan_v1c(fabric,pe_slots=256,domain_slots=256,fabric_slots_per_tick=768),
      CausalLinkPlanV1d(link_slots_per_tick=2,fabric_slots_per_tick=2,
       max_outbox_per_pe=128,max_link_span_ticks=256))
