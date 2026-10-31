"""V5-T3o (research only): C-authored A1b verdict mirrored into a terminal
channel, observed by two independent invocations of UNMODIFIED native-source BV v0e.

The dual channel passes are an observer-side research workaround: frozen BV v0e
accepts only one terminal_channel. Neither pass is an authenticated C sensor,
and the two passes do not constitute a single production BV executor.
"""
from __future__ import annotations
from dataclasses import asdict, replace
from spk_v5_research.island_c_owned_credit_v5t3h import (Measurement, ARMS, build_case, execute,
    CreditAdmissionError)
from spk_v5_research.island_online_credit_v5t3i import digest
from spk_architecture_v1.pe_fabric_v1a import plan_v1a
from spk_architecture_v1.pe_execution_v1b import execute_on_pes_v1b
from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
from spk_architecture_v1.causal_memory_v1c import uniform_causal_memory_plan_v1c
from spk_architecture_v1.causal_transport_v1d import CausalLinkPlanV1d
from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e, LiveBVPlanV0e

SCHEMA='spk-v5-t3opq-source-v0e-terminal-verdict-shadow-bridge/research-v0'
TERMINAL={1:30,-1:31}


def mirrored_case(m:Measurement, arm:str):
    """Add terminal mirror to *research C program*, align close with A marker at C.

    Neither frozen BV nor Architecture A1b source modules are modified.
    In particular the sensor input is still prepared by the host adapter.
    """
    original=build_case(m,arm)
    modified=[]
    for node in original.nodes:
        if node.node_id!='C':modified.append(node);continue
        instr=[]
        for op,value in node.instructions:
            instr.append((op,value))
            if op=='EMIT' and value in (11,12):
                instr.append(('EMIT',30 if value==11 else 31))
        modified.append(replace(node,instructions=tuple(instr)))
    closure=tuple(replace(e,timestamp=14) if (e.node_id=='C' and e.channel==6)
                  else e for e in original.events)
    return replace(original,nodes=tuple(modified),events=closure)


def _source_pass(case, fabric, assessed_channel):
    return execute_live_v0e(case,fabric,TransportPlanV1a(0,16),
        uniform_causal_service_plan_v1b(fabric,pe_slots=3,fabric_slots_per_tick=4),
        uniform_causal_memory_plan_v1c(fabric,pe_slots=256,domain_slots=256,fabric_slots_per_tick=768),
        CausalLinkPlanV1d(link_slots_per_tick=2,fabric_slots_per_tick=2,
                          max_outbox_per_pe=128,max_link_span_ticks=256),
        LiveBVPlanV0e(enabled=True,priority='forward-first',assessor='C',
                      terminal_channel=assessed_channel,max_ticks=256))


def evidence(m:Measurement,arm:str):
    """Source replay, not a signed attestation. Fail closed on missing causal lineage."""
    if arm not in ARMS:raise CreditAdmissionError('unknown research program')
    t3h=execute(m,arm)
    case=mirrored_case(m,arm)
    fabric=plan_v1a(case,'spread')
    core=execute_on_pes_v1b(case,fabric)['result']
    terminal_channels=[x['channel'] for x in core['emissions'] if x['node_id']=='C' and x['channel'] in (30,31)]
    if len(terminal_channels)>1:raise CreditAdmissionError('multiple C verdict mirrors')
    sign=(1 if terminal_channels==[30] else -1 if terminal_channels==[31] else None)
    passes={str(ch):_source_pass(case,fabric,ch) for ch in (30,31)}
    details={};assessed=[]
    for ch_str,r in passes.items():
        ch=int(ch_str);fb=r['feedback'];res=r['resources'];fwd=r['forward']
        terminals=[x for x in fwd['terminal'] if x['node_id']=='C' and x['channel']==ch]
        assessments=fb['assessments'];deliveries=fb['deliveries'];grants=fb['link_grants']
        if len(assessments)!=len(terminals):
            raise CreditAdmissionError('assessments not backed by actual source terminal')
        if assessments:
            assessed.append(ch)
            if len(assessments)!=1 or not assessments[0]['input_occurrences']:
                raise CreditAdmissionError('assessed C without source ancestry')
        if (res['bv_link_grants']!=len(grants) or
                res['bv_service_units']!=len(grants) or
                res['bv_memory_units']!=2*len(grants)):
            raise CreditAdmissionError('frozen BV resource accounting failure')
        if any(row['link_total']>2 for row in res['timeline']):
            raise CreditAdmissionError('source resource overcommit')
        if r['schema']!='spk-bv-live-dual-event-scheduler/v0e':
            raise CreditAdmissionError('wrong frozen BV source')
        details[ch_str]={
            'assessment_count':len(assessments),'terminal_count':len(terminals),
            'C_parent_occurrences':assessments[0]['input_occurrences'] if assessments else [],
            'grant_count':len(grants),'deliveries':[(x['sender'],x['receiver'],x['tick'],
                x['independent_receiver']) for x in deliveries],
            'resource_timeline_sha256':digest(res['timeline']),
            'original_source_result_sha256':digest(r),
            'resource_service_units':res['bv_service_units'],
            'resource_memory_units':res['bv_memory_units'],
        }
    if assessed!=([TERMINAL[sign]] if sign is not None else []):
        raise CreditAdmissionError('source terminal mirror differs from C A1b computation')
    if sign is not None and t3h['C_computed_verdict']!=sign:
        raise CreditAdmissionError('T3h C verdict source parity failure')
    active=details[str(TERMINAL[sign])] if sign is not None else None
    # A source BV witness is not a semantic reward, and cannot override a lost
    # semantic return, a missing host sensor, or a broken forward decision.
    admitted=bool(t3h['status']=='C_authored_credit_delivered' and sign is not None
         and active['assessment_count']==1 and active['grant_count']>=2
         and [(x[0],x[1]) for x in active['deliveries']]==[('C','B'),('B','A')]
         and all(x[3] for x in active['deliveries']) and
         t3h['A_consumed_credit']==sign)
    return {'schema':SCHEMA,'arm':arm,
        'measurement_sha256':digest(asdict(m)),
        'A1b_T3h_verdict':t3h['C_computed_verdict'],
        'A1b_T3h_status':t3h['status'],'terminal_verdict_sign':sign,
        'mirrored_C_terminal':TERMINAL[sign] if sign else None,
        'dual_frozen_BV_v0e_source_passes':details,
        'source_chain_C_to_B_to_A_valid':admitted,
        'research_admission':('SHADOW_SOURCE_REPLAY_ELIGIBLE' if admitted else 'REJECT_NO_UPDATE'),
        'no_native_semantic_BV_credit':True,
        'not_authenticated_sensor_or_signed_identity':True,
        'not_single_pass_native_BV':True}


def verify_evidence(m,arm,claim):
    if type(claim) is not dict or claim!=evidence(m,arm):
        raise CreditAdmissionError('forged/replayed/drifted source BV evidence')
    return True
