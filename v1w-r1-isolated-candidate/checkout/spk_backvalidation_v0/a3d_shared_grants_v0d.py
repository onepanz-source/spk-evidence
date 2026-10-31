"""BV v0d: A3d-anchored shared-credit overlay, forward spike grants are immutable.

This research bridge REUSES actual frozen A3d grants and contemporaneous PE and
memory reservations. It schedules BV packets into their residual capacities,
forward FIRST. It does NOT inject feedback in the live A3d scheduler, change
forward spike timings, or claim globally optimal/fair arbitration.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import replace

from search.spk_24n_independent_oracle_v0 import EventV0
from spk_architecture_v1.pe_fabric_v1a import plan_v1a
from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
from spk_architecture_v1.causal_memory_v1c import uniform_causal_memory_plan_v1c
from spk_architecture_v1.causal_transport_v1d import CausalLinkPlanV1d, execute_causal_transport_v1d
from spk_backvalidation_v0.contract_v0 import digest, validate_trace
from spk_backvalidation_v0.budgeted_feedback_v0c import transport_v0c, FeedbackTransportRejected
from spk_backvalidation_v0.simulator_evidence_v0b import NEW, OLD
from spk_backvalidation_v0.simulator_feedback_v0c import _case

SCHEMA = 'spk-bv-a3d-shared-grant-overlay/v0d'

class SharedGrantRejected(ValueError):
    pass


def _reject(message):
    raise SharedGrantRejected(message)


def actual_a3d_v0d(program=NEW, ticks=(1, 4), *,
                   link_slots=1, fabric_slots=1, inflight=2,
                   pe_slots=1, memory_slots=64, link_horizon=128):
    if program not in (NEW, OLD) or type(ticks) is not tuple or not ticks or len(ticks) > 8 or (
            any(type(t) is not int or t < 1 or t > 32 for t in ticks) or
            tuple(sorted(set(ticks))) != ticks):
        _reject('unadmitted event schedule')
    if any(type(x) is not int or x < 1 for x in
           (link_slots, fabric_slots, inflight, pe_slots, memory_slots, link_horizon)):
        _reject('invalid positive resource configuration')
    case = replace(_case(program, ticks[0]),
                   events=tuple(EventV0(t, 'A', 0) for t in ticks))
    fabric = plan_v1a(case, 'spread')
    tplan = TransportPlanV1a(0, inflight)
    pplan = uniform_causal_service_plan_v1b(
        fabric, pe_slots=pe_slots, fabric_slots_per_tick=pe_slots,
        max_service_span_ticks=link_horizon)
    mplan = uniform_causal_memory_plan_v1c(
        fabric, pe_slots=memory_slots, domain_slots=memory_slots,
        fabric_slots_per_tick=memory_slots,
        max_service_span_ticks=link_horizon)
    lplan = CausalLinkPlanV1d(link_slots, fabric_slots, 16, link_horizon)
    result = execute_causal_transport_v1d(case, fabric, tplan, pplan, mplan, lplan,
                                          max_batches=128, max_events=256)
    return case, fabric, (tplan, pplan, mplan, lplan), result


def trace_from_a3d_v0d(case, fabric, result):
    """Admit only unambiguous A->B->C event chains; fail closed on fan-in.

    Traces are constructed from A3d *executed* transfers and terminal events,
    not a guessed graph route. Event IDs refer to route occurrences in this
    bounded fixture, not a globally valid runtime event ID scheme.
    """
    if tuple((e.source_node, e.target_node, e.source_channel, e.target_channel,
              e.delay_ticks) for e in case.edges) != (('A','B',7,0,1),('B','C',7,0,1)):
        _reject('unsupported topology for A3d provenance bridge')
    if fabric.scheme != 'spread' or len(fabric.pe_ids) != 3:
        _reject('this bridge requires one node per PE')
    edges = [dict(id=f'e{i+1}',source=e.source_node,target=e.target_node,
                  source_channel=e.source_channel,target_channel=e.target_channel,
                  delay_ticks=e.delay_ticks) for i,e in enumerate(case.edges)]
    contexts = [dict(id='ctx-'+n.node_id,node_id=n.node_id,
                     program_sha256=digest(n.instructions),
                     features_sha256=digest({'reset_state': n.initial_raw}),
                     extractor_sha256=digest('a3d-reset-context-v0d'),
                     window_start=0,window_end=0) for n in case.nodes]
    batches = result['result']['observations']['batches']
    transfers = result['transport']['transfers']
    occurrences = []
    for i, r in enumerate(sorted(transfers, key=lambda x:(x['emission_timestamp'],x['source_node'],x['target_node']))):
        matching = [e for e in edges if (e['source'],e['target'],e['source_channel'],e['target_channel']) ==
                    (r['source_node'],r['target_node'],r['source_channel'],r['target_channel'])]
        if len(matching) != 1 or not r['cross_pe'] or r['delay_ticks'] < matching[0]['delay_ticks']:
            _reject('unobserved or ambiguous A3d transfer')
        sb = [b for b in batches if b['node_id'] == r['source_node'] and
              b['timestamp'] == r['emission_timestamp'] and r['source_channel'] in b['output_channels']]
        tb = [b for b in batches if b['node_id'] == r['target_node'] and
              b['timestamp'] == r['delivery_timestamp'] and r['target_channel'] in b['channels']]
        if len(sb) != 1 or len(tb) != 1:
            _reject('A3d transfer lacks unambiguous executed source/destination')
        if r['source_node'] == 'B':
            # Same-tick delivery identifies one causal A->B predecessor
            # within the accepted non-coalescing fixture. Reject other cases.
            parents = [o['id'] for o in occurrences if o['target'] == 'B' and
                       o['delivered_at'] == r['emission_timestamp']]
            if len(parents) != 1: _reject('ambiguous causal parent in A3d fixture')
        else:
            parents = []
        occurrences.append({'id':f'r{i+1}', 'source':r['source_node'],
            'target':r['target_node'],'emitted_at':r['emission_timestamp'],
            'delivered_at':r['delivery_timestamp'],'parent_ids':parents,
            'source_program_sha256': next(c['program_sha256'] for c in contexts if c['node_id']==r['source_node']),
            'source_context_id':'ctx-'+r['source_node'], 'edge_id':matching[0]['id'],
            'source_channel':r['source_channel'],'target_channel':r['target_channel']})
    terminals = result['result']['terminal_outputs']
    assessments, propagations = [], []
    for i, term in enumerate(terminals):
        if term['node_id'] != 'C' or term['channel'] != 7:
            _reject('unsupported terminal output')
        matches = [o for o in occurrences if o['target']=='C' and o['delivered_at']==term['timestamp']]
        if len(matches) != 1 or len(matches[0]['parent_ids']) != 1:
            _reject('terminal assessment has ambiguous causal parent')
        o=matches[0]
        aid=f'assessment-{i+1}'
        assessments.append({'id':aid,'occurrence_id':o['id'],'observer':'C',
            'observed_at':term['timestamp'],'observer_context_id':'ctx-C',
            'metric_id':'terminal-emission-present',
            'metric_policy_sha256':digest('terminal-emission-present-v0d'),
            'evidence_sha256':digest({'terminal':term,'transfer':o}),
            'status':'OBSERVED','value':1.0,'confidence':1.0,'reason':None})
        propagations.append({'id':f'prop-{i+1}', 'assessment_id':aid,
                             'path':[o['id'],o['parent_ids'][0]]})
    if sum(o['target']=='C' for o in occurrences) != len(terminals):
        _reject('undocumented terminal-chain mismatch')
    trace={'schema':'spk-back-validation-trace/v0','epoch':1,
           'topology_sha256':digest({'nodes':['A','B','C'],'edges':edges}),
           'budgets':dict(max_nodes=3,max_edges=2,max_contexts=3,max_occurrences=32,
               max_assessments=16,max_propagations=16,max_proposals=1,max_hops=4,max_parents=2),
           'contexts':contexts,'edges':edges,'occurrences':occurrences,
           'assessments':assessments,'propagations':propagations,'proposals':[]}
    validate_trace(trace)
    return trace


def _forward_ledger(result, fabric, plans):
    """Check exact A3d grants against executed cross-PE transfers."""
    transport, pe_plan, mem_plan, link = plans
    f = result['transport']['link_grants']
    t = result['transport']['transfers']
    if len(f) != len(t) or any(not x['cross_pe'] for x in t):
        _reject('forward grants/transfers not one-to-one')
    a=Counter((r['emission_timestamp'],r['source_node'],r['target_node'],
               r['source_channel'],r['target_channel'],r['delivery_timestamp']) for r in f)
    b=Counter((r['emission_timestamp'],r['source_node'],r['target_node'],
               r['source_channel'],r['target_channel'],r['delivery_timestamp']) for r in t)
    if a!=b: _reject('tampered A3d grant/transfer custody')
    service={r['tick']:r['fabric_grants'] for r in result['service']['timeline']}
    memory={r['tick']:r['fabric_units'] for r in result['memory']['timeline']}
    pe_used={(r['tick'],pe):used for r in result['service']['timeline'] for pe,used in r['pe_grants']}
    mem_pe={(r['tick'],pe):used for r in result['memory']['timeline'] for pe,used in r['pe_units']}
    mem_domains={(r['tick'],domain):used for r in result['memory']['timeline'] for domain,used in r['domain_units']}
    if any(x['tick']<0 or x['delivery_timestamp']<=x['tick'] or
           x['source_pe'] not in fabric.pe_ids or x['target_pe'] not in fabric.pe_ids or
           x['source_pe']==x['target_pe'] or
           x['source_pe']!=fabric.owner(x['source_node']) or
           x['target_pe']!=fabric.owner(x['target_node']) for x in f):
        _reject('invalid A3d forward link record')
    total=Counter(x['tick'] for x in f)
    perlink=Counter((x['tick'],x['source_pe'],x['target_pe']) for x in f)
    if any(count>link.fabric_slots_per_tick for count in total.values()) or any(
            count>link.link_slots_per_tick for count in perlink.values()):
        _reject('forward grants exceed plan')
    for rows,cap in ((service,pe_plan.fabric_slots_per_tick),
                     (memory,mem_plan.fabric_slots_per_tick)):
        if any(v>cap for v in rows.values()):_reject('frozen grant ledger overfull')
    # Report actual grants, not eventless guesses about all ticks.
    return f, total, perlink, service, memory, pe_used, mem_pe, mem_domains


def shared_overlay_v0d(result, fabric, plans, trace, *,
                       max_feedback_wait_ticks=32, cost_service=1,
                       cost_memory=2, feedback_hop_ticks=1):
    """Residual capacity reuses forward A3d service/link/memory grant budgets.

    A3d grants are fixed BEFORE overlay scheduling: spike priority is absolute.
    Thus feedback cannot affect the frozen spike stream or claim live coupling.
    """
    validate_trace(trace)
    if any(type(x) is not int or x<1 or x>10000 for x in
           (max_feedback_wait_ticks,cost_service,cost_memory,feedback_hop_ticks)):
        _reject('invalid bounded overlay parameters')
    # The current proxy defines one PE service grant and two memory-domain
    # permits (O at sender, E at receiver). Other costs require a new contract.
    if cost_service != 1 or cost_memory != 2:
        _reject('unsupported shared-credit proxy cost contract')
    transport_plan, pe_plan, memory_plan, link_plan = plans
    (grants,load,perlink,pe_used,mem_used,pe_pe,mem_pe,mem_domains) = _forward_ledger(result,fabric,plans)
    side=transport_v0c(trace,{'max_messages':64,'max_paths':64,'max_hops':4,
                    'max_elapsed_ticks':256,'max_feedback_operations':1024,
                    'max_memory_accesses':1024,'max_inflight':32,
                    'hop_latency':feedback_hop_ticks,'messages_per_link_per_tick':16})
    pending=sorted(side['packets'],key=lambda p:(p['hop'],p['assessment_id'],p['sender'],p['receiver']))
    delivered={}
    packets=[]
    conflict_counts=Counter()
    arrival_assessment={x['id']:x['observed_at'] for x in trace['assessments']}
    max_fwd=max((x['delivery_timestamp'] for x in grants),default=0)
    max_assess=max(arrival_assessment.values(),default=0)
    first=min([x['tick'] for x in grants]+list(arrival_assessment.values()) or [0])
    for packet in pending:
        a=packet['assessment_id'];hop=packet['hop'];src=packet['sender'];dst=packet['receiver']
        if src==dst: _reject('same-PE feedback not in admitted bridge domain')
        if src not in ('A','B','C') or dst not in ('A','B','C'):
            _reject('unexpected feedback node')
        sendpe=fabric.owner(src);recvpe=fabric.owner(dst)
        if sendpe==recvpe:_reject('local BV hop not in admitted shared-link domain')
        if hop>1 and (a,hop-1,src) not in delivered:
            _reject('feedback delivery missing causal predecessor')
        ready=max(arrival_assessment[a], packet['send_at'],
                  delivered.get((a,hop-1,src),0))
        chosen=None
        for t in range(ready,ready+max_feedback_wait_ticks+1):
            if t-first>=link_plan.max_link_span_ticks: _reject('joint logical horizon exceeded')
            if load[t]>=link_plan.fabric_slots_per_tick:
                conflict_counts['fabric_link']+=1;continue
            if perlink[(t,sendpe,recvpe)]>=link_plan.link_slots_per_tick:
                conflict_counts['directional_link']+=1;continue
            if pe_used.get(t,0)+cost_service>pe_plan.fabric_slots_per_tick or (
                    pe_pe.get((t,sendpe),0)+cost_service > dict(pe_plan.pe_slots)[sendpe]):
                conflict_counts['pe_service']+=1;continue
            if mem_used.get(t,0)+cost_memory>memory_plan.fabric_slots_per_tick or (
                    mem_pe.get((t,sendpe),0)+1>dict(memory_plan.pe_slots)[sendpe] or
                    mem_pe.get((t,recvpe),0)+1>dict(memory_plan.pe_slots)[recvpe] or
                    mem_domains.get((t,'O'),0)+1>dict(memory_plan.domain_slots)['O'] or
                    mem_domains.get((t,'E'),0)+1>dict(memory_plan.domain_slots)['E']):
                conflict_counts['memory']+=1;continue
            # Validate combined A3d + BV in-flight occupancy at injection time.
            forward_inflight=sum(x['tick']<=t<x['delivery_timestamp'] for x in grants)
            feedback_inflight=sum(x['send_at']<=t<x['delivered_at'] for x in packets)
            if forward_inflight+feedback_inflight>=transport_plan.max_inflight_occurrences:
                conflict_counts['inflight']+=1;continue
            chosen=t;break
        if chosen is None: _reject('feedback starvation under bounded shared credits')
        arrival=chosen+feedback_hop_ticks
        load[chosen]+=1;perlink[(chosen,sendpe,recvpe)]+=1
        pe_used[chosen]=pe_used.get(chosen,0)+cost_service
        pe_pe[(chosen,sendpe)]=pe_pe.get((chosen,sendpe),0)+cost_service
        mem_used[chosen]=mem_used.get(chosen,0)+cost_memory
        mem_pe[(chosen,sendpe)]=mem_pe.get((chosen,sendpe),0)+1
        mem_pe[(chosen,recvpe)]=mem_pe.get((chosen,recvpe),0)+1
        mem_domains[(chosen,'O')]=mem_domains.get((chosen,'O'),0)+1
        mem_domains[(chosen,'E')]=mem_domains.get((chosen,'E'),0)+1
        packet_record={**packet,'send_at':chosen,'delivered_at':arrival,
                       'source_pe':sendpe,'target_pe':recvpe,
                       'wait_extra_ticks':chosen-ready}
        packets.append(packet_record)
        delivered[(a,hop,dst)]=arrival
    # The bridge is *not* a live A3d executor; recorded spike timings unchanged.
    peak=max((sum(x['tick']<=t<x['delivery_timestamp'] for x in grants)+
              sum(x['send_at']<=t<x['delivered_at'] for x in packets)
              for t in range(first,max([max_fwd]+[p['delivered_at'] for p in packets])+1)),default=0)
    if peak>transport_plan.max_inflight_occurrences:_reject('joint in-flight bound exceeded')
    return {'schema':SCHEMA,'forward_a3d_sha256':digest(result),
            'feedback_trace_sha256':digest(trace),
            'forward_link_grants':len(grants),'feedback_link_grants':len(packets),
            'forward_grants_immutable':True,'grant_policy':'frozen-A3d-forward-first',
            'cost_proxy':{'service_per_feedback':cost_service,'memory_per_feedback':cost_memory,
                          'hop_ticks':feedback_hop_ticks},
            'feedback_packets':packets,'conflict_ticks':dict(sorted(conflict_counts.items())),
            'joint_peak_inflight':peak,'service_units_spent':len(packets)*cost_service,
            'memory_units_spent':len(packets)*cost_memory,
            'claims_excluded':['live-A3d-integration','feedback-induced-spike-delays',
                  'physical-memory-accesses','hardware-energy','global-credit',
                  'program-learning','program-promotion','general-N-node-runtime']}


def capture_v0d(ticks=(1,4)):
    base_case,base_f,base_plans,base=actual_a3d_v0d(OLD,ticks)
    cand_case,cand_f,cand_plans,cand=actual_a3d_v0d(NEW,ticks)
    if base['result']['terminal_outputs'] or base['transport']['transfers']:
        _reject('baseline emits unexpectedly')
    trace=trace_from_a3d_v0d(cand_case,cand_f,cand)
    overlay=shared_overlay_v0d(cand,cand_f,cand_plans,trace)
    return {'schema':SCHEMA,'ticks':list(ticks),
            'frozen_a3d_commit':'5af99cd1f4d603bf0c8e1557a6561c107765fdb5',
            'baseline_a3d_sha256':digest(base),'candidate_a3d_sha256':digest(cand),
            'candidate_terminal_events':len(cand['result']['terminal_outputs']),
            'feedback_trace':trace,'overlay':overlay,
            'note':'A3d forward execution fully complete before BV scheduling; forward grants immutable'}


def seal_v0d():
    from spk_backvalidation_v0.contract_v0 import canonical
    payload=capture_v0d()
    return canonical({'payload':payload,'payload_sha256':digest(payload)})


def verify_v0d(text):
    from spk_backvalidation_v0.contract_v0 import canonical,strict_loads
    obj=strict_loads(text)
    if (type(obj) is not dict or set(obj) != {'payload','payload_sha256'} or
            canonical(obj)!=text or digest(obj['payload'])!=obj['payload_sha256']):
        _reject('invalid or noncanonical v0d envelope')
    if obj != strict_loads(seal_v0d()):
        _reject('A3d/feedback re-execution mismatch (independent replay)')
    p=obj['payload']
    return {'status':'A3D_SHARED_GRANT_OVERLAY_REPLAY_PASS',
            'forward_spike_grants':p['overlay']['forward_link_grants'],
            'feedback_grants':p['overlay']['feedback_link_grants'],
            'forward_first_contention_ticks':p['overlay']['conflict_ticks'],
            'evidence_sha256':digest(obj),
            'note':'separate post-execution overlay, NOT live scheduler integration'}
