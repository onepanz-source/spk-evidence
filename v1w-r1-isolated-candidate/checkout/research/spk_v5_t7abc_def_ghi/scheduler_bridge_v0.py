"""T7ABC research bridge: genuine *unchanged* frozen BV-v0e scheduler, per epoch.

A3d/architecture contracts not edited. Each host-authored epoch re-admits a
three-neuron case. Channel 7 is a *structural* BV assessment by A: the positive
or negative outcome is a distinct A PE emission (21/22), inspected after the
run by an UNTRUSTED host adapter. Native BV packets do not carry this verdict.
"""
from __future__ import annotations
from dataclasses import replace
from research.spk_v5_t6abc_def_ghi.loop_v0 import require,digest

CHOICES=(11,12)
GOALS=(11,12)

class BridgeRejected(ValueError): pass

def check(ok,code):
    if not ok:raise BridgeRejected(code)

def case_for(choice,goal,*,drop_forward=False):
    """Source-type preserving construction; three admitted A/B/C neurons only.

    Uses original T3h case objects solely as typed constructors, not its
    decisions or causal measurements. Input is synthesized, not physical.
    """
    check(type(choice) is int and choice in CHOICES,'INVALID_CHOICE')
    check(type(goal) is int and goal in GOALS,'INVALID_GOAL')
    check(type(drop_forward) is bool,'INVALID_DROP_FLAG')
    from spk_v5_research.island_c_owned_credit_v5t3h import build_case,Measurement
    m=Measurement('2026-10-22 12:00:00','2026-10-22 12:01:00',12,12,420)
    original=build_case(m,'current')
    cprog=(('ACC',(1,1)),('CMP',1),('EMIT',choice),('RESET',0))
    bprog=(('ACC',(1,1)),('CMP',1),('EMIT',13),('RESET',0),
           ('ACC',(1,2)),('CMP',1),('EMIT',14),('RESET',0))
    aprog=(('ACC',(1,3)),('CMP',1),('EMIT',21 if goal==11 else 22),('EMIT',7),('RESET',0),
           ('ACC',(1,4)),('CMP',1),('EMIT',21 if goal==12 else 22),('EMIT',7),('RESET',0))
    programs={'C':cprog,'B':bprog,'A':aprog}
    nodes=tuple(replace(n,instructions=programs[n.node_id],initial_raw=0) for n in original.nodes)
    e=original.edges[0]
    edge_specs=[('C',11,'B',1),('C',12,'B',2),('B',13,'A',3),('B',14,'A',4)]
    if drop_forward:edge_specs=[]
    edges=tuple(replace(e,source_node=src,source_channel=sc,target_node=dst,
                        target_channel=tc,delay_ticks=1) for src,sc,dst,tc in edge_specs)
    inp=replace(original.events[0],timestamp=10,node_id='C',channel=1)
    case=replace(original,nodes=nodes,edges=edges,events=(inp,))
    check(len(case.nodes)==3 and {n.node_id for n in case.nodes}=={'C','B','A'},'UNSUPPORTED_TOPOLOGY')
    return case

def verify_source(source,choice,goal,*,drop_forward=False):
    """Inspect real frozen scheduler output, reject incomplete causal traversal.

    Source JSON is provided by the host and not independently authenticated.
    """
    check(type(source) is dict and source.get('schema')=='spk-bv-live-dual-event-scheduler/v0e','SOURCE_SCHEMA')
    f=source.get('forward');b=source.get('feedback');r=source.get('resources')
    check(all(type(x) is dict for x in (f,b,r)),'SOURCE_FIELDS')
    for section,fields in ((f,('batches','emissions','terminal','occurrences')), (b,('assessments','deliveries','link_grants')), (r,('timeline',))):
        check(all(type(section.get(field)) is list for field in fields),'SOURCE_LIST_FIELDS')
    check(type(source.get('constraints')) is list and 'no-learning' in source['constraints'],'FROZEN_CONSTRAINTS')
    emits=f['emissions']
    # Genuine PE-C, PE-B and PE-A emissions, not host-provided verdict labels.
    actual=lambda node,ch: [x for x in emits if x.get('node_id')==node and x.get('channel')==ch]
    check(len(actual('C',choice))==1 and len([x for x in emits if x.get('node_id')=='C'])==1,'C_PE_EMIT_DRIFT')
    expected_b=13 if choice==11 else 14
    expected_a=21 if choice==goal else 22
    if drop_forward:
        check(not [x for x in emits if x.get('node_id') in ('A','B')],'DROPPED_ROUTE_DID_NOT_QUIESCE')
        check(not b['assessments'] and not b['deliveries'] and not b['link_grants'],'DROP_CAUSED_PHANTOM_BV')
        check(not f['occurrences'],'DROP_HAS_OCCURRENCES')
        return {'C_choice':choice,'A_outcome':'ABSENT','A_emission':None,'C_B_A':False,
            'reverse_A_B_C':False,'full_BV_scheduler':True,'eligible_to_update':False,
            'source_sha256':digest(source),'source_batches':len(f['batches']),'source_bv_deliveries':0}
    check(len(actual('B',expected_b))==1 and len(actual('A',expected_a))==1 and len(actual('A',7))==1,'B_OR_A_PE_EMIT_DRIFT')
    check(len([x for x in emits if x.get('node_id')=='B'])==1,'B_DUPLICATE_OUTPUT')
    check(len([x for x in emits if x.get('node_id')=='A'])==2,'A_DUPLICATE_OUTPUT')
    check(len(f['occurrences'])==2,'FORWARD_OCCURRENCE_COUNT')
    o1,o2=f['occurrences']
    check((o1['source'],o1['target'],o1['channel'])==('C','B',1 if choice==11 else 2),'C_B_ROUTE')
    check((o2['source'],o2['target'],o2['channel'])==('B','A',3 if choice==11 else 4),'B_A_ROUTE')
    check(o1['id'] in o2['parents'] and o1['delivered_at'] is not None and o2['delivered_at'] is not None,'FORWARD_ANCESTRY')
    check(len(b['assessments'])==1 and b['assessments'][0]['observer']=='A' and
          o2['id'] in b['assessments'][0]['input_occurrences'],'A_ASSESSMENT_ANCESTRY')
    check(len(b['deliveries'])==2 and [(x['sender'],x['receiver']) for x in b['deliveries']]==
          [('A','B'),('B','C')],'REVERSE_BV_CHAIN')
    check(len(b['link_grants'])==2 and r.get('bv_link_grants')==2 and r.get('bv_service_units')==2 and
          r.get('bv_memory_units')==4,'BOUNDED_GRANT_RESOURCE_MISMATCH')
    check([x.get('node') for x in f['batches']]==['C','B','A'],'PE_BATCH_SEQUENCE')
    check(len(actual('A',21))+len(actual('A',22))==1,'AMBIGUOUS_A_JUDGMENT')
    return {'C_choice':choice,'A_outcome':'IMPROVED' if expected_a==21 else 'WORSENED',
        'A_emission':expected_a,'C_B_A':True,'reverse_A_B_C':True,
        'full_BV_scheduler':True,'eligible_to_update':True,
        'source_sha256':digest(source),'source_batches':len(f['batches']),
        'source_bv_deliveries':len(b['deliveries'])}

def execute_episode(choice,goal,*,drop_forward=False):
    """CALLS THE GENUINE FROZEN SCHEDULER (not a copied fork or PE-only fragment)."""
    from spk_architecture_v1.pe_fabric_v1a import plan_v1a
    from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
    from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
    from spk_architecture_v1.causal_memory_v1c import uniform_causal_memory_plan_v1c
    from spk_architecture_v1.causal_transport_v1d import CausalLinkPlanV1d
    from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e,LiveBVPlanV0e
    case=case_for(choice,goal,drop_forward=drop_forward)
    fabric=plan_v1a(case,'spread')
    source=execute_live_v0e(case,fabric,TransportPlanV1a(0,16),
        uniform_causal_service_plan_v1b(fabric,pe_slots=3,fabric_slots_per_tick=4),
        uniform_causal_memory_plan_v1c(fabric,pe_slots=256,domain_slots=256,fabric_slots_per_tick=768),
        CausalLinkPlanV1d(link_slots_per_tick=2,fabric_slots_per_tick=2,max_outbox_per_pe=128,max_link_span_ticks=256),
        LiveBVPlanV0e(enabled=True,priority='forward-first',assessor='A',terminal_channel=7,max_ticks=256))
    return verify_source(source,choice,goal,drop_forward=drop_forward)
