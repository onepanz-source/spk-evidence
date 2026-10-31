#!/usr/bin/env python3
"""T4DEF research: source-bound single BV-v0e invocation, static terminal 30.

D: source-custody and posthoc dual-replay forensic check.
E: single frozen BV v0e *invocation* with sign-independent C terminal channel.
F: differential truth table and no-semantic-promotion falsification.

Deliberate limitations: an independent T3h A1b execution still supplies the
semantic sign. The BV receiver only assesses a fixed C terminal, not the sign;
NO single-execution native semantic BV, native neural learning, sensor auth.
"""
from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import asdict, replace
from hashlib import sha256
import ast
import json
from pathlib import Path

BRIDGE_SHA = 'cbad4b447d294ad58c307f2bdc79c2dbc4933a23a21228d84bb5456ce58d1fef'
T3H_SHA = '9aced88cb5581732bd2c658bf23fb5149bf9d6aa7d40b5f499afe825b72c22a6'
FROZEN = {
    'spk_architecture_v1/pe_execution_v1b.py':'8e9d08ddc165e0c6e307ca16cc849feb7eabad33c148c26f4faa436c890d752c',
    'spk_backvalidation_v0/live_dual_scheduler_v0e.py':'2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9',
    'search/spk_bv_v0e_live_evidence.py':'1e93f1a71c1099a3ce3c5e14d2cb9cfa47b8bfa9027832785d9f09af0c2bbc70',
}
SOURCE_PINS = {
 'spk_v5_research/island_c_owned_credit_v5t3h.py':T3H_SHA,
 'spk_v5_research/island_online_credit_v5t3i.py':'804a5c1ccbddff116b6c6bc58a15d3ec09465dddb669b4ab4075b21363284c56',
 'spk_v5_research/island_source_admission_v5t3p.py':'811e0f8327c931736464d883a99cb53c75a14e58c6202d8a9c2ec1e0bd8d04e7',
 'spk_v5_research/island_source_bridge_audit_v5t3q.py':'fca2fe28df6723eaba0a289e7b45c62499af989d52acdcde0026847bcb45d84d',
 'spk_v5_research/island_source_bv_bridge_v5t3o.py':BRIDGE_SHA,
}
REFERENCE_SHA = '813753afd706eabff52653cf0a7674e1a44755981df61c6760fcbd4652c790d2'
DOSSIER_SHA = '01bf2f6181369bdbea1630e4eab0fa2bb576e431fee1ba372825c90ed910096d'
class BoundaryError(ValueError): pass

def require(ok, message):
    if not ok: raise BoundaryError(message)

def digest_bytes(p): return sha256(Path(p).read_bytes()).hexdigest()
def digest_json(v): return sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def verify_custody(root, dossier):
    root=Path(root).resolve()
    require(Path(dossier).is_file() and digest_bytes(dossier)==DOSSIER_SHA, 'T4ABC_DOSSIER_SHA_INVALID')
    data=json.loads(Path(dossier).read_text())
    require(data['status']=='SOURCE_BOUNDARY_LOCALIZED_NATIVE_SEMANTIC_VERDICT_UNPROVEN','DOSSIER_STATUS_INVALID')
    require(data['single_pass_C_authored_semantic_verdict_proven'] is False,'DOSSIER_PROMOTION_INVALID')
    require(data['A_evidence_custody']['original_t3opq_sha256']==REFERENCE_SHA,'REFERENCE_REPORT_SHA_INVALID')
    pinned={**FROZEN,**SOURCE_PINS}
    for rel,expected in pinned.items():
        path=root/rel
        require(path.is_file() and not path.is_symlink(),'SOURCE_MISSING_OR_SYMLINK:'+rel)
        require(digest_bytes(path)==expected,'SOURCE_SHA_DRIFT:'+rel)
    return pinned

def dual_replay_locus(source):
    """Return AST evidence; fail closed if original source call topology drifts."""
    code=Path(source).read_text(); tree=ast.parse(code)
    evidence=next((f for f in tree.body if isinstance(f,ast.FunctionDef) and f.name=='evidence'),None)
    require(evidence is not None,'BRIDGE_EVIDENCE_NOT_FOUND')
    calls=[x for x in ast.walk(evidence) if isinstance(x,ast.Call) and isinstance(x.func,ast.Name)]
    names=Counter(x.func.id for x in calls)
    require(names['_source_pass']==1 and names['execute_on_pes_v1b']==1,'ORIGINAL_BRIDGE_TOPOLOGY_DRIFT')
    comps=[n for n in ast.walk(evidence) if isinstance(n,ast.DictComp)]
    dual=any(any(isinstance(x,ast.Name) and x.id=='_source_pass' for x in ast.walk(c)) for c in comps)
    require(dual and 'passes={str(ch):_source_pass(case,fabric,ch) for ch in (30,31)}' in code,
            'ORIGINAL_DUAL_REPLAY_SELECTION_NOT_FOUND')
    require('assessed!=([TERMINAL[sign]]' in code,'ORIGINAL_POSTHOC_SIGN_SELECTION_NOT_FOUND')
    return {'function':'evidence','line':evidence.lineno,'call_expressions':dict(names),
            'original_calls_two_source_passes':True,'posthoc_sign_selection':True,
            'authority':'source-AST-only'}

def fixed_terminal_case(m,arm,build_case_func):
    """One terminal channel 30 for C positive OR negative, sign not encoded."""
    original=build_case_func(m,arm)
    seen=False
    nodes=[]
    for node in original.nodes:
        if node.node_id!='C':nodes.append(node);continue
        seen=True; instr=[]
        for op,val in node.instructions:
            instr.append((op,val))
            if op=='EMIT' and val in (11,12): instr.append(('EMIT',30))
        nodes.append(replace(node,instructions=tuple(instr)))
    require(seen,'C_NEURON_MISSING')
    closure=tuple(replace(e,timestamp=14) if e.node_id=='C' and e.channel==6 else e for e in original.events)
    return replace(original,nodes=tuple(nodes),events=closure)

def evaluate_source_result(result, semantic_witness):
    """Validate source receipts strictly; NEVER equate a terminal receipt with sign."""
    require(type(result) is dict and result.get('schema')=='spk-bv-live-dual-event-scheduler/v0e','BV_SOURCE_SCHEMA_INVALID')
    for key in ('forward','feedback','resources'):
        require(type(result.get(key)) is dict,'BV_SOURCE_FIELD_INVALID:'+key)
    fwd=result['forward'];fb=result['feedback'];res=result['resources']
    for key in ('terminal',):require(type(fwd.get(key)) is list,'SOURCE_TERMINALS_INVALID')
    for key in ('assessments','deliveries','link_grants'):
        require(type(fb.get(key)) is list,'SOURCE_FEEDBACK_FIELD_INVALID:'+key)
    for key in ('timeline',):require(type(res.get(key)) is list,'RESOURCE_TIMELINE_INVALID')
    terms=[x for x in fwd['terminal'] if x.get('node_id')=='C' and x.get('channel')==30]
    require(len(terms)<=1,'DUPLICATE_FIXED_TERMINAL')
    assessments=fb['assessments']; deliveries=fb['deliveries'];grants=fb['link_grants']
    require(len(assessments)==len(terms),'UNBACKED_C_ASSESSMENT')
    if assessments:
        require(len(assessments)==1 and bool(assessments[0].get('input_occurrences')),'NO_C_SOURCE_ANCESTRY')
    require(res.get('bv_link_grants')==len(grants) and res.get('bv_service_units')==len(grants) and
            res.get('bv_memory_units')==2*len(grants),'BV_RESOURCE_DRIFT')
    require(all(x.get('link_total',10000)<=2 for x in res['timeline']),'BV_RESOURCE_OVERCOMMIT')
    sign=semantic_witness.get('C_computed_verdict')
    require(sign in (1,-1,None),'SEMANTIC_SIGN_INVALID')
    # T3h witnesses are derived from a SEPARATE A1b execution; do not infer sign from terminal 30.
    require(len(terms)==int(sign is not None),'FIXED_TERMINAL_SEMANTIC_MIRROR_MISMATCH')
    c_chain=(len(assessments)==1 and len(grants)>=2 and
             [(x.get('sender'),x.get('receiver')) for x in deliveries]==[('C','B'),('B','A')] and
             all(x.get('independent_receiver') is True for x in deliveries))
    eligible=bool(c_chain and semantic_witness.get('status')=='C_authored_credit_delivered' and
                  semantic_witness.get('A_consumed_credit')==sign)
    return {'T3h_separate_A1b_sign':sign,'source_fixed_terminal_count':len(terms),
            'source_assessment_count':len(assessments),'source_grants':len(grants),
            'source_C_B_A_structural_chain':bool(c_chain),'research_structural_eligible':eligible,
            'source_timeline_sha256':digest_json(res['timeline']),
            'source_receipt_sha256':digest_json(result),
            'source_transmits_semantic_sign':False,'single_native_semantic_BV':False}

def run_one(m,arm):
    """Real source invocation. Separate T3h A1b semantic execution disclosed."""
    from spk_v5_research.island_c_owned_credit_v5t3h import execute,build_case
    from spk_architecture_v1.pe_fabric_v1a import plan_v1a
    from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
    from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
    from spk_architecture_v1.causal_memory_v1c import uniform_causal_memory_plan_v1c
    from spk_architecture_v1.causal_transport_v1d import CausalLinkPlanV1d
    from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e,LiveBVPlanV0e
    witness=execute(m,arm) # A1b semantic result, separate from below BV run.
    case=fixed_terminal_case(m,arm,build_case)
    fabric=plan_v1a(case,'spread')
    source=execute_live_v0e(case,fabric,TransportPlanV1a(0,16),
        uniform_causal_service_plan_v1b(fabric,pe_slots=3,fabric_slots_per_tick=4),
        uniform_causal_memory_plan_v1c(fabric,pe_slots=256,domain_slots=256,fabric_slots_per_tick=768),
        CausalLinkPlanV1d(link_slots_per_tick=2,fabric_slots_per_tick=2,max_outbox_per_pe=128,max_link_span_ticks=256),
        LiveBVPlanV0e(enabled=True,priority='forward-first',assessor='C',terminal_channel=30,max_ticks=256))
    outcome=evaluate_source_result(source,witness)
    return {'arm':arm,'measurement_sha256':digest_json(asdict(m)),
            'T3h_status':witness['status'],**outcome}

def table_cases():
    from spk_v5_research.island_c_owned_credit_v5t3h import ARMS,Measurement
    stamps=('2026-10-22 12:00:00','2026-10-22 12:01:00')
    for prev in (12,350):
      for now in (12,350):
        for co2 in (420,850,None):
          for arm in ARMS:
            for failure in ('none','no_C','no_marker','no_forward','no_reverse'):
                m=Measurement(*stamps,prev,now,co2 if failure!='no_C' else None,
                    sensor_visible=(co2 is not None and failure!='no_C'),
                    send_decision=failure!='no_marker',forward_enabled=failure!='no_forward',
                    reverse_enabled=failure!='no_reverse')
                yield {'context':f'{int(prev>=200)}{int(now>=200)}',
                       'C_sensor':None if co2 is None else co2>=600,'arm':arm,'failure':failure},m,arm

def run_report(root,dossier):
    pins=verify_custody(root,dossier)
    locus=dual_replay_locus(Path(root)/'spk_v5_research/island_source_bv_bridge_v5t3o.py')
    rows=[];counts=Counter();signs=Counter()
    for case,m,arm in table_cases():
        try:
            observed=run_one(m,arm)
        except Exception as exc:
            raise BoundaryError('SOURCE_CASE_FAILURE:'+str(case)+':'+str(exc)) from exc
        counts['eligible' if observed['research_structural_eligible'] else 'rejected']+=1
        if observed['T3h_separate_A1b_sign'] in (1,-1):signs[str(observed['T3h_separate_A1b_sign'])]+=1
        rows.append({**case,**observed})
    require(len(rows)==180,'TABLE_WRONG_CASE_COUNT')
    # Against original dual-run T3OPQ baseline, without equating structural and semantic proof.
    reference_parity=(counts['eligible']==42 and counts['rejected']==138 and
                      signs['1']==36 and signs['-1']==36)
    require(verify_custody(root,dossier)==pins,'SOURCE_DRIFT_DURING_SINGLE_BV_RESEARCH')
    return {'schema':'spk-v5-t4def-single-source-fixed-terminal/research-v0',
       'status':('SINGLE_BV_SOURCE_STRUCTURAL_PARITY_PASS' if reference_parity
                 else 'SINGLE_BV_SOURCE_STRUCTURAL_PARITY_DIFFERENCE'),
       'D_host_dual_replay_locus':locus,
       'E_one_source_BV_invocation_per_case':True,
       'E_separate_T3h_A1b_invocation_per_case':True,
       'E_source_receives_semantic_sign':False,
       'F_case_count':len(rows),'F_research_structural_eligible':counts['eligible'],
       'F_rejected':counts['rejected'],'F_semantic_sign_counts':dict(signs),
       'F_reference_structural_parity':reference_parity,
       'F_rows_sha256':digest_json(rows),
       'F_cases':rows,
       'source_sha256':pins,'T4ABC_dossier_sha256':DOSSIER_SHA,
       'T3OPQ_report_sha256':REFERENCE_SHA,
       'limits':['Static channel 30 cannot encode sign 11 vs 12',
            'T3h sign comes from an independent A1b execution, not the BV v0e receipt',
            'Only one frozen BV call per case; NOT one full native computation',
            'C CO2 threshold host-prepared, no authenticated sensor or goal authority',
            'No native policy update or receiver-readable signed semantic verdict',
            'Same research environment/fixtures as T3OPQ, no independent blind test'],
       'native_semantic_BV_proven':False,'native_learning_proven':False,
       'single_native_semantic_execution_proven':False,'promotion_allowed':False}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,required=True);ap.add_argument('--dossier',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    try:
        require(not args.out.exists(),'OUTPUT_EXISTS_USE_NEW_FILENAME')
        report=run_report(args.root,args.dossier)
        args.out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
        print('T4DEF ONE BV SOURCE PER EPISODE',report['status'],'NO NATIVE SEMANTIC BV')
        print('cases',report['F_case_count'],'eligible',report['F_research_structural_eligible'],
              'sha256',digest_bytes(args.out))
    except (BoundaryError,OSError,ValueError,KeyError,TypeError) as exc:
        raise SystemExit('T4DEF FAIL CLOSED: '+str(exc))
if __name__=='__main__':main()
