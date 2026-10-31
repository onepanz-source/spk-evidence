#!/usr/bin/env python3
"""SPK V5 T4GHI: genuine one BV source call, source-output inspection only.

T4G: sign indistinguishability of the fixed-terminal structural projection.
T4H: new source execution (one execute_live_v0e / episode, no T3h.execute).
T4I: strictly observation-scoped sign/receiver custody, no native promotion.

The historical T4DEF sign is used exclusively as a posthoc falsification comparator.
It cannot generate an accepted C sign or grant native credit.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from research.spk_v5_t4def import t4def as prev

REFERENCE_SHA='02169ef1000ef9a0864e331ff9d6ae8ca05c4523c4c2d48cf589c86a14be13d3'
PREV_CODE_SHA='b5262709d40714811fe91bfa28389afb8f3a8edc847eb21e5564b677d3516945'
PRIOR_PRODUCER_SHA='813753afd706eabff52653cf0a7674e1a44755981df61c6760fcbd4652c790d2'
STATUS='SINGLE_SOURCE_SIGN_VISIBILITY_RESEARCH_ONLY'
SCHEMA='spk-v5-t4ghi-single-source-sign-observability/research-v0'
MAX_ROWS=180

class GateError(ValueError):pass

def need(test,msg):
    if not test:raise GateError(msg)

def sha_bytes(path):return sha256(Path(path).read_bytes()).hexdigest()
def digest(v):return prev.digest_json(v)

def read_reference(path):
    need(Path(path).is_file(),'T4DEF_REFERENCE_MISSING')
    need(sha_bytes(path)==REFERENCE_SHA,'T4DEF_REFERENCE_SHA_DRIFT')
    d=json.loads(Path(path).read_text())
    need(d.get('status')=='SINGLE_BV_SOURCE_STRUCTURAL_PARITY_PASS','T4DEF_REFERENCE_STATUS_INVALID')
    need(d.get('T3OPQ_report_sha256')==PRIOR_PRODUCER_SHA,'T3OPQ_PIN_MISMATCH')
    need(d.get('E_one_source_BV_invocation_per_case') is True and d.get('E_separate_T3h_A1b_invocation_per_case') is True,'T4DEF_PROVENANCE_INVALID')
    need(d.get('E_source_receives_semantic_sign') is False and d.get('promotion_allowed') is False,'T4DEF_NONPROMOTION_INVALID')
    need(d.get('F_case_count')==MAX_ROWS and len(d.get('F_cases',[]))==MAX_ROWS,'T4DEF_CASE_COUNT_INVALID')
    need(d.get('F_reference_structural_parity') is True and d.get('F_research_structural_eligible')==42,'T4DEF_PARITY_INVALID')
    return d

def custody(root):
    root=Path(root)
    needed={'research/spk_v5_t4def/t4def.py':PREV_CODE_SHA,**prev.FROZEN,**prev.SOURCE_PINS}
    for rel,sha in needed.items():
        p=root/rel
        need(p.is_file() and not p.is_symlink(),'MISSING_OR_SYMLINK:'+rel)
        need(sha_bytes(p)==sha,'SOURCE_SHA_DRIFT:'+rel)
    return needed

def structural_nonidentifiability(rows):
    """C terminal + C/B/A grants and resource-timeline cannot encode sign.

    Deliberately does not include full receipt digest: it can differ for other
    reasons and should not be equated with receiver-readable semantic sign.
    """
    signed=[x for x in rows if x['T3h_separate_A1b_sign'] in (-1,1)]
    groups=defaultdict(set)
    for x in signed:
        key=(x['source_fixed_terminal_count'],x['source_assessment_count'],x['source_grants'],
             x['source_C_B_A_structural_chain'],x['source_timeline_sha256'])
        groups[key].add(x['T3h_separate_A1b_sign'])
    ambiguous=sum(v=={-1,1} for v in groups.values())
    need(len(signed)==72 and Counter(x['T3h_separate_A1b_sign'] for x in signed)==Counter({1:36,-1:36}),'T4DEF_SIGN_COUNTS_CHANGED')
    need(ambiguous>0,'NO_STRUCTURAL_AMBIGUITY_FOUND')
    return {'historical_sign_rows':len(signed),'structural_signature_groups':len(groups),
            'groups_with_both_signs':ambiguous,'terminal_projection_sign_identifiable':False,
            'full_source_result_sign_identifiable':'UNTESTED_NOT_INFERRED_FROM_HASH'}

def _walk_emission_lists(obj:Any,path='forward',depth=0):
    """Discover *declared emissions* only; avoid terminal/assessment/input records.

    Records are candidates observed in returned Python data, not authenticated
    neuron-authored packets. Unknown payload shape is treated as no observation.
    """
    if depth>12:return
    if isinstance(obj,dict):
        for key,value in obj.items():
            k=str(key)
            if (k=='emissions' or k.endswith('_emissions')) and type(value) is list:
                for i,event in enumerate(value):
                    if type(event) is dict and type(event.get('node_id')) is str and type(event.get('channel')) is int and type(event.get('timestamp')) is int:
                        yield path+'.'+k+'['+str(i)+']',event
            elif isinstance(value,(dict,list)):
                yield from _walk_emission_lists(value,path+'.'+k,depth+1)
    elif isinstance(obj,list):
        for i,item in enumerate(obj):
            if isinstance(item,(dict,list)):yield from _walk_emission_lists(item,path+'['+str(i)+']',depth+1)

def observe_forward_result(source):
    need(type(source) is dict and source.get('schema')=='spk-bv-live-dual-event-scheduler/v0e','BV_SOURCE_SCHEMA_INVALID')
    forward=source.get('forward');fb=source.get('feedback');res=source.get('resources')
    need(type(forward) is dict and type(fb) is dict and type(res) is dict,'BV_TOPLEVEL_FIELDS_INVALID')
    terminals=forward.get('terminal')
    need(type(terminals) is list,'BV_TERMINAL_FIELD_INVALID')
    terms=[x for x in terminals if isinstance(x,dict) and x.get('node_id')=='C' and x.get('channel')==30]
    need(len(terms)<=1,'C30_MULTIPLICITY_INVALID')
    assessments=fb.get('assessments');deliveries=fb.get('deliveries');grants=fb.get('link_grants')
    need(all(type(x) is list for x in (assessments,deliveries,grants)),'BV_RECEIPT_FIELDS_INVALID')
    need(len(assessments)==len(terms),'UNBACKED_ASSESSMENT')
    need(all(bool(x.get('input_occurrences')) for x in assessments),'SOURCE_PARENT_MISSING')
    need(res.get('bv_link_grants')==len(grants) and res.get('bv_service_units')==len(grants) and res.get('bv_memory_units')==2*len(grants),'BV_RESOURCE_DRIFT')
    timeline=res.get('timeline')
    need(type(timeline) is list and all(isinstance(x,dict) and type(x.get('link_total')) is int and 0<=x.get('link_total')<=2 for x in timeline),'BV_TIMELINE_INVALID')
    entries=list(_walk_emission_lists(forward))
    focus=[(p,e) for p,e in entries if (e['node_id'],e['channel']) in {('C',11),('C',12),('B',13),('B',14),('A',13),('A',14)}]
    by_role={}
    for role,allowed in (('C',(11,12)),('B',(13,14)),('A',(13,14))):
        role_rows=[(p,e) for p,e in focus if e['node_id']==role and e['channel'] in allowed]
        # The same event might be repeated at multiple producer result paths.
        distinct={(e['timestamp'],e['node_id'],e['channel']) for _,e in role_rows}
        need(len(distinct)<=1,'CONTRADICTORY_SOURCE_EMISSIONS_'+role)
        by_role[role]=({'channel':next(iter(distinct))[2],'timestamp':next(iter(distinct))[0],
                        'paths':sorted(set(p for p,_ in role_rows))} if distinct else None)
    c=by_role['C'];b=by_role['B'];a=by_role['A']
    visible_sign=1 if c and c['channel']==11 else -1 if c and c['channel']==12 else None
    consistent=bool(c and b and a and (c['channel']==11)==(b['channel']==13)==(a['channel']==13)
                    and c['timestamp']<b['timestamp']<a['timestamp'])
    # Do not count mere exposure in a host return as a native BV semantic grant.
    return {'forward_output_keys':sorted(forward.keys()),'declared_emissions_seen':len(entries),
            'C_sign_candidate_from_same_source_forward_output':visible_sign,
            'C_B_A_emission_candidate_consistent':consistent,
            'event_candidate_paths':by_role,'C_fixed_terminal_count':len(terms),
            'BV_assessment_count':len(assessments),'BV_grant_count':len(grants),
            'BV_delivery_roles':[(x.get('sender'),x.get('receiver')) for x in deliveries],
            'source_terminal_only_does_not_encode_sign':True,
            'signed_C_to_A_native_BV_receipt_proven':False,'native_learning_proven':False}

def source_once(measurement,arm):
    """Exactly one BV source call; no independent T3h.execute or A1b replay."""
    from spk_v5_research.island_c_owned_credit_v5t3h import build_case
    from spk_architecture_v1.pe_fabric_v1a import plan_v1a
    from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
    from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
    from spk_architecture_v1.causal_memory_v1c import uniform_causal_memory_plan_v1c
    from spk_architecture_v1.causal_transport_v1d import CausalLinkPlanV1d
    from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e,LiveBVPlanV0e
    case=prev.fixed_terminal_case(measurement,arm,build_case)
    fabric=plan_v1a(case,'spread')
    source=execute_live_v0e(case,fabric,TransportPlanV1a(0,16),
        uniform_causal_service_plan_v1b(fabric,pe_slots=3,fabric_slots_per_tick=4),
        uniform_causal_memory_plan_v1c(fabric,pe_slots=256,domain_slots=256,fabric_slots_per_tick=768),
        CausalLinkPlanV1d(link_slots_per_tick=2,fabric_slots_per_tick=2,max_outbox_per_pe=128,max_link_span_ticks=256),
        LiveBVPlanV0e(enabled=True,priority='forward-first',assessor='C',terminal_channel=30,max_ticks=256))
    return source

def run(root,reference):
    pins=custody(root)
    prev_run=read_reference(reference)
    projection=structural_nonidentifiability(prev_run['F_cases'])
    runs=[]; counts=Counter()
    for i,((ident,measurement,arm),historical) in enumerate(zip(prev.table_cases(),prev_run['F_cases'])):
        need(ident['arm']==historical['arm'] and ident['failure']==historical['failure'] and ident['context']==historical['context'] and ident['C_sensor']==historical['C_sensor'],'T4DEF_ORDER_DRIFT')
        need(digest(__import__('dataclasses').asdict(measurement))==historical['measurement_sha256'],'T4DEF_MEASUREMENT_DRIFT')
        source=source_once(measurement,arm)
        src_digest=digest(source)
        # Comparison is read-only: historical T3h sign NEVER enters producer/observer.
        need(src_digest==historical['source_receipt_sha256'],'SOURCE_REEXECUTION_DRIFT_CASE_'+str(i))
        obs=observe_forward_result(source)
        if obs['C_sign_candidate_from_same_source_forward_output'] is not None:
            need(obs['C_sign_candidate_from_same_source_forward_output']==historical['T3h_separate_A1b_sign'],'C_EMISSION_SIGN_MISMATCH_CASE_'+str(i))
        cls='SAME_SOURCE_EMISSION_CANDIDATE' if obs['C_sign_candidate_from_same_source_forward_output'] is not None else 'SOURCE_SIGN_NOT_EXPOSED'
        counts[cls]+=1
        if obs['C_B_A_emission_candidate_consistent']:counts['C_B_A_EMISSION_CANDIDATE_CONSISTENT']+=1
        runs.append({'index':i,**ident,'source_sha256':src_digest,'status':cls,**obs})
    need(len(runs)==MAX_ROWS,'COVERAGE_DRIFT')
    return {'schema':SCHEMA,'status':STATUS,'source_pins':pins,'T4DEF_reference_sha256':REFERENCE_SHA,
            'D_structure_nonidentifiability':projection,'G_single_BV_per_case':True,
            'G_separate_A1b_verdict_execution':False,'H_count':MAX_ROWS,
            'H_statuses':dict(sorted(counts.items())),'H_rows':runs,
            'I_no_native_semantic_BV':True,'I_no_signed_sensor':True,'I_no_native_learning':True,
            'I_no_blind':True,'promotion_allowed':False,
            'limits':['C semantic channels 11/12 are present in source case program, but return schema might not expose authored emissions',
                      'source emission candidates in host Python result are not authenticated end-to-end receiver-readable semantic BV packets',
                      'T4DEF reference sign used only after execution as falsification comparator',
                      'structural parity is assessed against T4DEF source receipts, same checkout, not independent hardware',
                      'no genuine independent sensor authority, no blind goal evidence, no native actor learning']}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    need(not a.out.exists(),'OUTPUT_EXISTS')
    try:
        result=run(a.root,a.reference)
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n')
        print('T4GHI',result['status'],'cases',result['H_count'],'source_sign_observed',result['H_statuses'].get('SAME_SOURCE_EMISSION_CANDIDATE',0))
        print('structural dual-sign signatures',result['D_structure_nonidentifiability']['groups_with_both_signs'])
        print('sha256',sha_bytes(a.out))
    except (GateError,prev.BoundaryError,ValueError,TypeError,KeyError,OSError) as e:
        raise SystemExit('T4GHI FAIL CLOSED: '+str(e))
if __name__=='__main__':main()
