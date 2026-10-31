#!/usr/bin/env python3
"""SPK V5 T4NOP read-only native receiver *boundary* research gate.

N: exact T4JKLM report, code and frozen SHA custody.
O: reexecute each of the 180 actual BV-v0e source cases exactly once and
   independently inventory the receiver delivery records, without manufacturing
   an authored semantic receipt from source emissions.
P: receiver-authentication necessary-condition audit and adversarial rejects;
   even syntactically complete host-built evidence is never promoted.

Nothing here signs packets, grants semantic credit, or changes frozen code.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from research.spk_v5_t4jkl_fix import t4jkl_fix as predecessor
from research.spk_v5_t4ghi import t4ghi as bv

SCHEMA='spk-v5-t4nop-receiver-boundary/research-v0'
STATUS='RECEIVER_SEMANTIC_BOUNDARY_OBSERVED_BUT_NOT_AUTHENTICATED'
REF_SHA='29623afe61f35cae178b25383a5cf7621b212d4128d586cba011433da7c7bd74'
PRED_CODE_SHA='e425b447ed73a6355d4faec6209526e58334c865e3d897537d0bd01bdcd03b73'
MAX_CASES=180
EXPECTED_DELIVERY_FIELDS=frozenset({'assessment_id','evidence_ids','independent_receiver','packet_id','receiver','sender','tick'})
SEMANTIC_REQUIRED=frozenset({'semantic_sign','C_emission_id','authenticator','source_identity','causal_parent_id'})

class GateError(ValueError): pass

def need(value,reason):
    if not value:raise GateError(reason)

def sha(path):return sha256(Path(path).read_bytes()).hexdigest()

def canonical_sha(value):
    return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def load_reference(path):
    path=Path(path)
    need(path.is_file() and not path.is_symlink(),'REFERENCE_MISSING_OR_SYMLINK')
    need(sha(path)==REF_SHA,'REFERENCE_SHA_DRIFT')
    r=json.loads(path.read_bytes())
    need(r.get('schema')==predecessor.SCHEMA and r.get('status')==predecessor.STATUS,'REFERENCE_SCHEMA_DRIFT')
    need(r.get('L_same_source_reexecution_count')==MAX_CASES and r.get('L_source_result_parity_180') is True and
         r.get('L_recipe_flag_comparisons_180') is True,'REFERENCE_PARITY_INVALID')
    need(r.get('native_receiver_semantic_receipt_proven') is False and r.get('native_learning_proven') is False and
         r.get('promotion_allowed') is False,'REFERENCE_NATIVE_PROMOTION_FORGERY')
    expected={'NO_SOURCE_SIGN':108,'NO_CAUSAL_EMISSION_TRIPLE':24,
              'APPLICATION_FORWARD_GUARD_BLOCK':24,'RESEARCH_GUARD_ELIGIBLE_NOT_NATIVE_CREDIT':24}
    need(r.get('K_offline',{}).get('classification_counts')==expected,'REFERENCE_CLASS_DRIFT')
    rows=r.get('L_rows')
    need(type(rows) is list and len(rows)==MAX_CASES,'REFERENCE_CASE_DRIFT')
    for i,x in enumerate(rows):
        need(type(x) is dict and x.get('index')==i and type(x.get('source_sha256')) is str and len(x['source_sha256'])==64,'REFERENCE_ROW_INVALID_'+str(i))
        need(x.get('native_semantic_receipt_proven') is False,'REFERENCE_ROW_PROMOTION_'+str(i))
    return r

def custody(root,reference):
    root=Path(root)
    code=root/'research/spk_v5_t4jkl_fix/t4jkl_fix.py'
    need(code.is_file() and not code.is_symlink() and sha(code)==PRED_CODE_SHA,'T4JKLM_SOURCE_PIN_DRIFT')
    pins={'research/spk_v5_t4jkl_fix/t4jkl_fix.py':PRED_CODE_SHA,**predecessor.custody(root)}
    need(pins==reference['J_source_pins'] | {'research/spk_v5_t4jkl_fix/t4jkl_fix.py':PRED_CODE_SHA},'SOURCE_PIN_SET_DRIFT')
    return pins

def field_inventory(forward_sign: int|None, deliveries:Any, candidate_class:str):
    """Field-level receiver evidence only. Emits NO credit/authorization.

    A synthetic payload with perfect fields is still not a native C-authored
    message; observed keys are necessary but never sufficient for promotion.
    """
    need(candidate_class in ('NO_SOURCE_SIGN','NO_CAUSAL_EMISSION_TRIPLE',
           'APPLICATION_FORWARD_GUARD_BLOCK','RESEARCH_GUARD_ELIGIBLE_NOT_NATIVE_CREDIT'), 'CLASS_INVALID')
    need(forward_sign in (None,-1,1) and type(forward_sign) in (int,type(None)),'SIGN_INVALID')
    need(type(deliveries) is list and all(type(d) is dict for d in deliveries),'DELIVERY_SHAPE_INVALID')
    need(len(deliveries) in (0,2),'DELIVERY_COUNT_INVALID')
    fields=frozenset(k for delivery in deliveries for k in delivery)
    for d in deliveries:
        need(set(d)==set(fields),'DELIVERY_FIELD_INCONSISTENT')
    need(fields in (frozenset(),EXPECTED_DELIVERY_FIELDS),'UNREVIEWED_RECEIVER_SCHEMA')
    for d in deliveries:
        if deliveries:
            need(all(type(d[k]) in (str,int) and bool(d[k]) for k in ('packet_id','assessment_id')),'DELIVERY_ID_INVALID')
            need(all(type(d[k]) is str and d[k] for k in ('sender','receiver')),'DELIVERY_ROUTE_ID_INVALID')
            need(type(d['tick']) is int,'DELIVERY_TICK_INVALID')
            need(type(d['independent_receiver']) is bool,'INDEPENDENT_RECEIVER_FLAG_INVALID')
            need(type(d['evidence_ids']) in (list,tuple),'DELIVERY_EVIDENCE_IDS_INVALID')
    # More fields do not confer trusted authorship. Unknown fields require a new review,
    # rather than quietly declaring the current port sufficient.
    if len(deliveries)==2:
        need([(d['sender'],d['receiver']) for d in deliveries]==[('C','B'),('B','A')], 'DELIVERY_ROUTE_INVALID')
    missing=sorted(SEMANTIC_REQUIRED-fields)
    # Strictly no caller-controlled positive predicate in this research port.
    return {'delivery_count':len(deliveries),'delivery_fields':sorted(fields),
            'source_emission_sign_visible':forward_sign is not None,
            'missing_semantic_fields':missing,
            'semantic_sign_in_receiver_delivery':False,
            'native_source_authentication_verifiable':False,
            'native_receiver_semantic_credit':False,
            'research_classification':candidate_class}

def evaluate_claimed_receipt(payload:Any):
    """Shadow schema feasibility; cannot turn supplied host dictionaries into trust.

    Used for adversarial tests to ensure spoofing source/sign/metadata doesn't
    cause the research port to accept a native verdict.
    """
    need(type(payload) is dict,'RECEIPT_NOT_MAPPING')
    missing=sorted(SEMANTIC_REQUIRED-set(payload))
    if missing:return {'status':'MISSING_SEMANTIC_BINDING','missing':missing,'native_credit':False}
    sign=payload.get('semantic_sign')
    if type(sign) is not int or sign not in (-1,1):
        return {'status':'INVALID_SIGN','missing':[],'native_credit':False}
    if payload.get('source_identity')!='C':
        return {'status':'INVALID_AUTHOR_CLAIM','missing':[],'native_credit':False}
    if not isinstance(payload.get('C_emission_id'),str) or not payload['C_emission_id']:
        return {'status':'INVALID_EMISSION_ID','missing':[],'native_credit':False}
    if not isinstance(payload.get('causal_parent_id'),str) or not payload['causal_parent_id']:
        return {'status':'INVALID_CAUSAL_PARENT','missing':[],'native_credit':False}
    # An 'authenticator' field fabricated by an untrusted host is just a string.
    return {'status':'UNTRUSTED_AUTHENTICATOR_NO_NATIVE_VERIFIER','missing':[],
            'native_credit':False}

def shape_collision(sign_rows):
    """Same *schema* for opposite signs, NOT a claim full records are identical."""
    groups=defaultdict(set)
    for r in sign_rows:
        if r['observed_sign'] not in (-1,1):continue
        key=(tuple(r['delivery_fields']),r['delivery_count'],
             tuple(tuple(edge) for edge in r['delivery_routes']),r['research_classification'])
        groups[key].add(r['observed_sign'])
    dual=sum(s=={-1,1} for s in groups.values())
    need(dual>0,'NO_POSITIVE_NEGATIVE_RECEIVER_SHAPE_COLLISION')
    return {'receiver_schema_groups':len(groups),'dual_sign_receiver_schema_groups':dual,
            'scope':'field and route shape only; payload IDs and values may differ'}

def run(root,ref_path):
    reference=load_reference(ref_path)
    pins=custody(root,reference)
    old=bv.read_reference(Path(root)/'research/spk_v5_t4ghi/reference/t4def-single-source.json')
    ghi=predecessor.reference(Path(root)/'research/spk_v5_t4jkl/reference/t4ghi-one-pass-sign.json')
    need(len(ghi['H_rows'])==MAX_CASES and len(old['F_cases'])==MAX_CASES,'UPSTREAM_COVERAGE_DRIFT')
    rows=[];count=Counter();emission_counts=Counter()
    for i,((ident,measurement,arm),hist,ghi_row,prev_row) in enumerate(zip(
             bv.prev.table_cases(),old['F_cases'],ghi['H_rows'],reference['L_rows'])):
        need(ghi_row['index']==i and prev_row['index']==i,'CASE_ORDER_DRIFT_'+str(i))
        need(all(ident[k]==ghi_row[k] for k in ('context','C_sensor','failure','arm')),'CASE_RECIPE_DRIFT_'+str(i))
        need(bv.digest(asdict(measurement))==hist['measurement_sha256'],'INPUT_MEASUREMENT_DRIFT_'+str(i))
        source=bv.source_once(measurement,arm)
        dgst=bv.digest(source)
        need(dgst==prev_row['source_sha256']==ghi_row['source_sha256']==hist['source_receipt_sha256'],
             'SOURCE_REPLAY_SHA_DRIFT_'+str(i))
        obs=bv.observe_forward_result(source)
        sign=obs['C_sign_candidate_from_same_source_forward_output']
        need(sign==ghi_row['C_sign_candidate_from_same_source_forward_output'],'C_SIGN_DRIFT_'+str(i))
        need(obs['event_candidate_paths']==ghi_row['event_candidate_paths'],'EMISSION_PATH_DRIFT_'+str(i))
        checked=predecessor.checked_row(ghi_row)
        need(checked['classification']==prev_row['classification'],'CLASSIFICATION_DRIFT_'+str(i))
        deliveries=source['feedback']['deliveries']
        v=field_inventory(sign,deliveries,checked['classification'])
        need(predecessor.visible_event_schema(source)=={
             **prev_row['receiver_field_inventory']},'RECEIVER_PREDECESSOR_INVENTORY_DRIFT_'+str(i))
        need(v['delivery_fields']==prev_row['receiver_field_inventory']['delivery_field_names']
             and v['delivery_count']==prev_row['receiver_field_inventory']['feedback_delivery_count'],
             'RECEIVER_SCHEMA_DRIFT_'+str(i))
        count[checked['classification']]+=1
        if sign is not None:emission_counts['sign_visible']+=1
        if obs['C_B_A_emission_candidate_consistent']:emission_counts['emission_triple']+=1
        routes=[[x.get('sender'),x.get('receiver')] for x in deliveries]
        rows.append({'index':i,'source_sha256':dgst,
          'research_classification':checked['classification'],
          'observed_sign':sign,'delivery_count':len(deliveries),
          'delivery_fields':v['delivery_fields'],'delivery_routes':routes,
          'receipt_sign_verified':False,'native_source_authentication_verified':False,
          'native_receiver_semantic_credit':False})
    need(dict(sorted(count.items()))==reference['K_offline']['classification_counts'],'CASE_PARTITION_DRIFT')
    need(emission_counts==Counter({'sign_visible':72,'emission_triple':48}),'SOURCE_SIGN_COUNTS_DRIFT')
    collisions=shape_collision(rows)
    need(sum(r['native_receiver_semantic_credit'] for r in rows)==0,'UNSAFE_CREDIT_PROMOTION')
    need(custody(root,reference)==pins,'SOURCE_CUSTODY_CHANGED_DURING_RUN')
    return {'schema':SCHEMA,'status':STATUS,
        'N_T4JKLM_report_sha256':REF_SHA,'N_source_pins':pins,
        'O_case_count':len(rows),'O_single_source_BV_calls':len(rows),
        'O_sign_observations':emission_counts['sign_visible'],
        'O_emission_triples':emission_counts['emission_triple'],
        'O_research_guard_count':count['RESEARCH_GUARD_ELIGIBLE_NOT_NATIVE_CREDIT'],
        'O_classification_counts':dict(sorted(count.items())),
        'O_delivery_keys':sorted(EXPECTED_DELIVERY_FIELDS),
        'O_missing_semantic_contract_fields':sorted(SEMANTIC_REQUIRED),
        'O_cross_sign_receiver_shape':collisions,
        'O_rows':rows,
        'P_untrusted_receipt_probe':evaluate_claimed_receipt({
          'semantic_sign':1,'C_emission_id':'host-test',
          'authenticator':'host-test','source_identity':'C',
          'causal_parent_id':'host-test'}),
        'P_native_semantic_credit_accepted':0,
        'P_trusted_native_authenticator_available':False,
        'native_receiver_semantic_receipt_proven':False,
        'native_learning_proven':False,'promotion_allowed':False,
        'limits':['Source forward.emissions includes C channel 11/12 on 72 cases but those are producer return data, not receiver messages',
                  'BV-v0e feedback.deliveries records only packet/assessment/evidence/route/tick fields in this experiment',
                  'Same schema and route can occur with opposite semantic signs; this does not prove full payload bytes indistinguishable',
                  'Neither explicit sign binding nor trusted C-authored authentication present at receiver boundary',
                  'Source SHA custody and programmatic host payload assembly are not native neuronal authorship',
                  'No independent signed sensor or independent reward/goal truth; no online learning update']}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--reference',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    try:
        need(not args.out.exists(),'OUTPUT_ALREADY_EXISTS')
        result=run(args.root,args.reference)
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n')
        print('T4NOP',result['status'],'180 native source replays; 72 signs; 24 guard-only cases; native receipts 0')
        print('SHA256',sha(args.out))
    except (GateError,predecessor.GateError,bv.GateError,bv.prev.BoundaryError,
            ValueError,TypeError,KeyError,AssertionError,OSError) as e:
        raise SystemExit('T4NOP FAIL CLOSED: '+str(e))

if __name__=='__main__':main()
