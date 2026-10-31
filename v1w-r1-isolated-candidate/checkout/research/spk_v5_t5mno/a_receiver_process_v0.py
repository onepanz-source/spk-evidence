"""A-only process. Inbound envelope excludes C sign, host fault and goal fields.

Computes local synthetic observations even if no C receipt arrives, demonstrating
structural separation from the C-output transport. Host controls this process,
its policy and measurements; this is NOT independent authenticated evidence.
"""
from __future__ import annotations
from .a_local_outcome_v0 import synthetic_A_observation,evaluate_observation,require
from collections import Counter
from hashlib import sha256
import argparse,json,re
from pathlib import Path

SHA=re.compile(r'^[0-9a-f]{64}$')
SCHEMA='spk-v5-t5mno-A-local-outcome-process/research-v0'

def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(v):return sha256(canonical(v)).hexdigest()

def compute(inbound):
    require(type(inbound) is list and len(inbound)==180,'RECEIVER_INPUT_COUNT')
    seen=set();out=[];cnt=Counter()
    for item in inbound:
        require(type(item) is dict and set(item)=={'case_index','source_sha256','receipt_present'},'RECEIVER_ALLOWED_FIELDS')
        i=item['case_index'];sha=item['source_sha256'];present=item['receipt_present']
        require(type(i) is int and 0<=i<180 and i not in seen,'RECEIVER_CASE_ORDER_OR_DUPLICATE')
        require(i==len(out),'RECEIVER_NONCANONICAL_ORDER')
        require(type(sha) is str and bool(SHA.fullmatch(sha)),'RECEIVER_SHA')
        require(type(present) is bool,'RECEIVER_RECEIPT_FLAG')
        seen.add(i)
        local=synthetic_A_observation(i);v=evaluate_observation(local)
        cnt[v['outcome']]+=1
        if present:cnt['paired_receipts']+=1;cnt['paired_'+v['outcome']]+=1
        out.append({'case_index':i,'source_sha256':sha,'C_receipt_present':present,
                    'A_local_observation_sha256':digest(local),'A_local_goal':local['goal'],
                    'A_local_error_before':v['error_before'],'A_local_error_after':v['error_after'],
                    'A_structural_assessment':v['assessment'],'A_outcome':v['outcome'],
                    'paired_research_only':present,'A_external_authenticated':False,
                    'A_causally_attributed_to_C':False,'native_credit':False})
    require(len(seen)==180,'RECEIVER_INCOMPLETE')
    return {'schema':SCHEMA,'status':'A_LOCAL_STRUCTURAL_EVALUATION_HOST_PROVISIONED',
        'cases':180,'new_C_compute_calls':0,'new_BV_scheduler_calls':0,
        'A_local_synthetic_observations':180,'A_local_judgments':180,
        'A_paired_research_outcomes':cnt['paired_receipts'],
        'outcome_counts':dict(sorted(cnt.items())),
        'A_authenticated_sensor_observations':0,'A_authenticated_independent_judgments':0,
        'C_causal_effect_attributed':0,'native_BV_credit':0,'native_learning':False,
        'promotion_allowed':False,'rows':out,'rows_sha256':digest(out)}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    try:
        require(args.input.is_file() and not args.input.is_symlink(),'INBOUND_NOT_FILE')
        require(not args.out.exists(),'OUTPUT_EXISTS')
        result=compute(json.loads(args.input.read_bytes()))
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_bytes((json.dumps(result,sort_keys=True,indent=2)+'\n').encode())
        print('T5MNO A RECEIVER',result['status'],'observations',180,'paired',result['A_paired_research_outcomes'],'authenticated',0)
    except (ValueError,TypeError,KeyError,OSError) as ex:
        raise SystemExit('T5MNO A FAIL CLOSED: '+str(ex))
if __name__=='__main__':main()
