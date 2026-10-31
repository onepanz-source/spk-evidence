#!/usr/bin/env python3
"""SPK V5 T4JKL cumulative research gate: semantic emission vs action/receiver custody.

J: Custody of prior one-pass source evidence.
K: Negative-control classification, separating action delivery from BV emissions.
L: Independent-process, single-source re-execution and receiver-payload field audit.
No alteration of frozen source; no native semantic BV or neural policy promotion.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from research.spk_v5_t4ghi import t4ghi as prev

SCHEMA='spk-v5-t4jkl-emission-action-receiver-custody/research-v0'
STATUS='SAME_SOURCE_SIGN_WITH_APPLICATION_CUSTODY_GUARD_RESEARCH_ONLY'
REFERENCE_SHA='dc98a1a5e45270d665e5119540ae960e405f4d02b703bd0c52d04202873abef3'
PREV_SHA='9f58dc3e0db338b1c42bb1117f6ccbc2e08fc72ac0311fef6618b25e6cdc967d'
MAX_ROWS=180
class GateError(ValueError):pass

def need(ok,msg):
    if not ok: raise GateError(msg)

def file_sha(p):return sha256(Path(p).read_bytes()).hexdigest()

def digest(v):return prev.digest(v)

def reference(path):
    p=Path(path)
    need(p.is_file() and not p.is_symlink(),'REFERENCE_MISSING_OR_SYMLINK')
    need(file_sha(p)==REFERENCE_SHA,'T4GHI_REFERENCE_SHA_DRIFT')
    d=json.loads(p.read_bytes())
    need(d.get('status')=='SINGLE_SOURCE_SIGN_VISIBILITY_RESEARCH_ONLY' and d.get('schema')==prev.SCHEMA,'PREDECESSOR_STATUS_OR_SCHEMA_DRIFT')
    need(d.get('G_single_BV_per_case') is True and d.get('G_separate_A1b_verdict_execution') is False,'PREDECESSOR_CALL_TOPOLOGY_INVALID')
    need(d.get('H_count')==MAX_ROWS and type(d.get('H_rows')) is list and len(d['H_rows'])==MAX_ROWS,'PREDECESSOR_COVERAGE_INVALID')
    need(d.get('promotion_allowed') is False and all(d.get(k) is True for k in ('I_no_blind','I_no_native_learning','I_no_native_semantic_BV','I_no_signed_sensor')),'PREDECESSOR_NONPROMOTION_INVALID')
    need(d.get('H_statuses',{}).get('SAME_SOURCE_EMISSION_CANDIDATE')==72 and d.get('H_statuses',{}).get('SOURCE_SIGN_NOT_EXPOSED')==108,'PREDECESSOR_COUNTS_INVALID')
    return d

def custody(root):
    root=Path(root)
    pins={'research/spk_v5_t4ghi/t4ghi.py':PREV_SHA,
          'research/spk_v5_t4ghi/reference/t4def-single-source.json':prev.REFERENCE_SHA,
          **prev.custody(root)}
    for rel,dgst in pins.items():
        f=root/rel
        need(f.is_file() and not f.is_symlink() and file_sha(f)==dgst,'ROOT_SOURCE_DRIFT:'+rel)
    return pins

def checked_row(row):
    need(type(row) is dict and type(row.get('index')) is int,'ROW_INDEX_INVALID')
    need(row.get('status') in ('SAME_SOURCE_EMISSION_CANDIDATE','SOURCE_SIGN_NOT_EXPOSED'),'ROW_STATUS_INVALID')
    need(row.get('failure') in ('none','no_C','no_marker','no_forward','no_reverse'),'FAILURE_CLASS_INVALID')
    need(row.get('arm') in ('current','persist','silent'),'ARM_INVALID')
    need(row.get('context') in ('00','01','10','11'),'CONTEXT_INVALID')
    need(type(row.get('C_sensor')) is bool or row.get('C_sensor') is None,'SENSOR_INVALID')
    need(row.get('source_terminal_only_does_not_encode_sign') is True and row.get('signed_C_to_A_native_BV_receipt_proven') is False,'INVALID_PROMOTION')
    sign=row.get('C_sign_candidate_from_same_source_forward_output')
    need(type(sign) is int and sign in (-1,1) or sign is None,'SIGN_INVALID')
    by_role=row.get('event_candidate_paths')
    need(type(by_role) is dict and set(by_role)=={'C','B','A'},'EVENT_ROLE_KEYS_INVALID')
    for k in ('C','B','A'):
        event=by_role[k]
        if event is None:continue
        need(type(event) is dict and type(event.get('channel')) is int and type(event.get('timestamp')) is int and type(event.get('paths')) is list and bool(event['paths']),'EVENT_SHAPE_INVALID_'+k)
        need(all(type(x) is str and x.startswith('forward.') for x in event['paths']),'FORGED_EVENT_ORIGIN_'+k)
    c,b,a=(by_role.get(k) for k in ('C','B','A'))
    need(sign is None if c is None else sign==(1 if c['channel']==11 else -1 if c['channel']==12 else 0),'C_SIGN_CHANNEL_DRIFT')
    need(row.get('status')==('SAME_SOURCE_EMISSION_CANDIDATE' if sign is not None else 'SOURCE_SIGN_NOT_EXPOSED'),'SIGN_STATUS_MISMATCH')
    need(type(row.get('C_B_A_emission_candidate_consistent')) is bool,'EVENT_CONSISTENCY_INVALID')
    locally_consistent=bool(c and b and a and (c['channel'],b['channel'],a['channel']) in ((11,13,13),(12,14,14)) and c['timestamp']<b['timestamp']<a['timestamp'])
    need(locally_consistent==row['C_B_A_emission_candidate_consistent'],'EVENT_ORDER_OR_SIGN_CONSISTENCY_DRIFT')
    need(type(row.get('BV_grant_count')) is int and 0<=row['BV_grant_count']<=2,'GRANT_COUNT_INVALID')
    need(type(row.get('BV_assessment_count')) is int and 0<=row['BV_assessment_count']<=1,'ASSESSMENT_COUNT_INVALID')
    need(type(row.get('C_fixed_terminal_count')) is int and 0<=row['C_fixed_terminal_count']<=1,'TERMINAL_COUNT_INVALID')
    need(row['C_fixed_terminal_count']==row['BV_assessment_count'],'ASSESSMENT_TERMINAL_DRIFT')
    need(type(row.get('BV_delivery_roles')) is list,'DELIVERY_ROLES_INVALID')
    actual=[tuple(p) for p in row['BV_delivery_roles']]
    need(actual in ([],[('C','B'),('B','A')]),'DELIVERY_ROLES_DRIFT')
    if sign is None:need(not locally_consistent,'INVENTED_SIGN_PATH')
    # This is a research-only eligibility *guard*, NOT receiver-authenticated semantic credit.
    action_allowed=row['failure'] not in ('no_forward','no_marker')
    credit_return_allowed=row['failure']!='no_reverse'
    research_guard=bool(sign is not None and locally_consistent and action_allowed and credit_return_allowed and row['failure']=='none')
    # Missing observer evidence and failed action/return must not be counted as native learning.
    classification=(
        'NO_SOURCE_SIGN' if sign is None else
        'NO_CAUSAL_EMISSION_TRIPLE' if not locally_consistent else
        'APPLICATION_FORWARD_GUARD_BLOCK' if not action_allowed else
        'REVERSE_GUARD_BLOCK' if not credit_return_allowed else
        'RESEARCH_GUARD_ELIGIBLE_NOT_NATIVE_CREDIT')
    return {'index':row['index'],'failure':row['failure'],'context':row['context'],'arm':row['arm'],
            'sign':sign,'BV_emission_triple':locally_consistent,
            'application_action_forward_enabled':action_allowed,
            'application_reverse_enabled':credit_return_allowed,
            'research_guard_eligible':research_guard,
            'classification':classification,
            'source_sha256':row['source_sha256'],
            'native_semantic_receipt_proven':False,'native_learning_proven':False}

def offline_analysis(d):
    rows=d['H_rows'];out=[];by_class=Counter();by_failure=defaultdict(Counter)
    for i,row in enumerate(rows):
        need(row.get('index')==i,'ROW_INDEX_DRIFT')
        x=checked_row(row);out.append(x);by_class[x['classification']]+=1;by_failure[x['failure']][x['classification']]+=1
    need(by_class==Counter({'NO_SOURCE_SIGN':108,'NO_CAUSAL_EMISSION_TRIPLE':24,'APPLICATION_FORWARD_GUARD_BLOCK':24,'RESEARCH_GUARD_ELIGIBLE_NOT_NATIVE_CREDIT':24}),'NEGATIVE_CONTROL_COUNTS_DRIFT')
    need(sum(x['BV_emission_triple'] for x in out)==48,'TRIPLE_COUNT_DRIFT')
    need(sum(x['research_guard_eligible'] for x in out)==24,'RESEARCH_GUARD_COUNT_DRIFT')
    need(Counter(x['sign'] for x in out)==Counter({None:108,1:36,-1:36}),'SIGN_DISTRIBUTION_DRIFT')
    return {'classification_counts':dict(sorted(by_class.items())),
            'failure_classification':{k:dict(sorted(v.items())) for k,v in sorted(by_failure.items())},
            'emission_triple_count':48,'research_guard_eligible_count':24,
            'unpromoted_count':180,'rows_sha256':digest(out)}

def visible_event_schema(source):
    """Descriptive field inventory, no speculation about native receipt authorship.

    Even an explicit id or parent reference is not an authenticated sensor signal.
    """
    need(type(source) is dict and all(type(source.get(k)) is dict for k in ('forward','feedback','resources')),'SOURCE_SCHEMA_MISSING')
    from research.spk_v5_t4ghi.t4ghi import _walk_emission_lists
    focus=[]
    for p,e in _walk_emission_lists(source['forward']):
        if (e.get('node_id'),e.get('channel')) in {('C',11),('C',12),('B',13),('B',14),('A',13),('A',14)}:
            focus.append((p,e))
    deliveries=source['feedback'].get('deliveries')
    need(type(deliveries) is list,'DELIVERY_LIST_MISSING')
    need(all(type(e) is dict for e in deliveries),'DELIVERY_SHAPE_DRIFT')
    event_keys=sorted({k for _,e in focus for k in e.keys()})
    delivery_keys=sorted({k for e in deliveries for k in e.keys()})
    return {'candidate_emission_count':len(focus),'emission_field_names':event_keys,
            'feedback_delivery_count':len(deliveries),'delivery_field_names':delivery_keys,
            'native_authentication_evident':False,'receiver_readable_sign_receipt_proven':False}

def run(root,reference_file):
    pins=custody(root)
    d=reference(reference_file)
    hist=prev.read_reference(Path(root)/'research/spk_v5_t4ghi/reference/t4def-single-source.json')
    off=offline_analysis(d)
    observed=[];schemas=Counter()
    # Re-run frozen scheduler once per case, no A1b separate.
    for i,((ident,m,arm),old,historical) in enumerate(zip(prev.prev.table_cases(),d['H_rows'],hist['F_cases'])):
        need(all(ident[k]==old[k] for k in ('context','C_sensor','failure','arm')),'SOURCE_INPUT_DRIFT_'+str(i))
        need(digest(asdict(m))==historical['measurement_sha256'],'T4DEF_MEASUREMENT_DRIFT_'+str(i))
        actual=prev.source_once(m,arm)
        dgst=digest(actual)
        need(dgst==old['source_sha256']==historical['source_receipt_sha256'],'SOURCE_RECEIPT_BYTE_DRIFT_'+str(i))
        o=prev.observe_forward_result(actual)
        for key in ('C_sign_candidate_from_same_source_forward_output','C_B_A_emission_candidate_consistent','C_fixed_terminal_count','BV_assessment_count','BV_grant_count','event_candidate_paths','BV_delivery_roles'):
            need(json.loads(json.dumps(o[key]))==old[key],'SOURCE_EVENT_OBSERVATION_DRIFT_'+str(i)+'_'+key)
        checked=checked_row(old)
        need(checked['application_action_forward_enabled']==bool(m.forward_enabled),'ACTION_FORWARD_FLAG_MISMATCH_'+str(i))
        need(checked['application_reverse_enabled']==bool(m.reverse_enabled),'REVERSE_FLAG_MISMATCH_'+str(i))
        inventory=visible_event_schema(actual)
        schemas[(tuple(inventory['emission_field_names']),tuple(inventory['delivery_field_names']))]+=1
        observed.append({'index':i,'source_sha256':dgst,'classification':checked['classification'],
                         'receiver_field_inventory':inventory,
                         'native_semantic_receipt_proven':False})
    need(custody(root)==pins,'ROOT_CUSTODY_CHANGED_DURING_RUN')
    need(len(observed)==MAX_ROWS and len(schemas)>0,'EMPTY_SOURCE_AUDIT')
    return {'schema':SCHEMA,'status':STATUS,
            'T4GHI_reference_sha256':REFERENCE_SHA,
            'J_source_pins':pins,'J_original_report_pin_verified':True,
            'K_offline':off,'L_same_source_reexecution_count':len(observed),
            'L_source_result_parity_180':True,
            'L_receiver_field_schemas':[{'emission_field_names':list(a),'delivery_field_names':list(b),'cases':n}
                 for (a,b),n in sorted(schemas.items(),key=lambda kv:(kv[0],kv[1]))],
            'L_rows':observed,
            'native_receiver_semantic_receipt_proven':False,'native_learning_proven':False,
            'authenticated_sensor_authority_proven':False,'promotion_allowed':False,
            'limits':['Application no_forward can still show C/B/A BV emission candidates, so emission parity does not prove A action custody',
                      'CPython event/delivery fields and SHA custody do not authenticate a C-origin semantic receipt',
                      'One frozen BV scheduler invocation per case, but no receiver-native semantic credit transaction',
                      'No independently authenticated sensor or independent goal truth; no learning update']}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    need(not a.out.exists(),'OUTPUT_EXISTS')
    try:
        r=run(a.root,a.reference)
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+'\n')
        print('T4JKL',r['status'],'cases',r['L_same_source_reexecution_count'],
              'guard_research',r['K_offline']['research_guard_eligible_count'])
        print('sha256',file_sha(a.out))
    except (GateError,prev.GateError,prev.prev.BoundaryError,ValueError,TypeError,KeyError,OSError,AssertionError) as ex:
        raise SystemExit('T4JKL FAIL CLOSED: '+str(ex))
if __name__=='__main__':main()
