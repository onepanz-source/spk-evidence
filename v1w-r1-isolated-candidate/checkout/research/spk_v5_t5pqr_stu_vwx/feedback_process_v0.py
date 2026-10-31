"""Three process-visible stages for synthetic A->B->C research shadow feedback.
No secret material, hardware attestation, or permission for any native credit.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from .causal_contract_v0 import need,canonical,digest,CausalBoundary

FIELDS={'sequence','case_index','source_sha256','a_observation_sha256','a_outcome',
        'causally_attributed_to_C','sensor_authenticated','native_credit',
        'native_learning','classification'}


def valid_packet(row,idx):
    need(type(row) is dict and set(row)==FIELDS,'FEEDBACK_PACKET_SCHEMA')
    need(type(row['sequence']) is int and row['sequence']==idx,'SEQUENCE_REPLAY_OR_DRIFT')
    need(type(row['case_index']) is int and 0<=row['case_index']<180,'CASE_INVALID')
    need(row['a_outcome'] in ('IMPROVED','UNCHANGED','WORSENED'),'OUTCOME_INVALID')
    for k in ('source_sha256','a_observation_sha256'):
        v=row[k];need(type(v) is str and len(v)==64 and all(ch in '0123456789abcdef' for ch in v),'INVALID_SHA_'+k)
    need(row['causally_attributed_to_C'] is False and row['sensor_authenticated'] is False and row['native_credit'] is False and row['native_learning'] is False,'NATIVE_CREDIT_FORBIDDEN')
    need(row['classification']=='RESEARCH_ONLY_A_LOCAL_FEEDBACK','CLASSIFICATION_MISMATCH')


def issue(packets):
    need(type(packets) is list and len(packets)==24,'A_PACKET_COUNT')
    seen=set();prev='0'*64;out=[]
    for i,row in enumerate(packets):
        valid_packet(row,i)
        need(row['case_index'] not in seen,'CASE_DUPLICATE')
        seen.add(row['case_index'])
        entry={'packet':row,'previous':prev,'A_entry_sha256':digest({'packet':row,'previous':prev})}
        prev=entry['A_entry_sha256'];out.append(entry)
    return {'stage':'A','entries':out,'end_sha256':prev,'native_BV_credit':0,'native_learning':False}


def relay(a):
    need(type(a) is dict and set(a)=={'stage','entries','end_sha256','native_BV_credit','native_learning'} and a['stage']=='A','BAD_A_DOC')
    need(a['native_BV_credit']==0 and a['native_learning'] is False,'BAD_A_PROMOTION')
    need(type(a['entries']) is list and len(a['entries'])==24,'RELAY_COUNT')
    previous='0'*64;last_idx=-1;out=[]
    for i,e in enumerate(a['entries']):
        need(type(e) is dict and set(e)=={'packet','previous','A_entry_sha256'},'A_ENTRY_SCHEMA')
        valid_packet(e['packet'],i)
        need(e['packet']['case_index']>last_idx,'OUT_OF_ORDER_CASE')
        last_idx=e['packet']['case_index']
        need(e['previous']==previous,'A_LEDGER_CHAIN_BROKEN')
        expected=digest({'packet':e['packet'],'previous':previous})
        need(e['A_entry_sha256']==expected,'A_ENTRY_FORGERY_UNCHAINED')
        previous=expected
        out.append({'a_entry':e,'B_relay_sha256':digest({'A_entry_sha256':expected,'B_seq':i})})
    need(a['end_sha256']==previous,'A_TERMINAL_SHA_DRIFT')
    return {'stage':'B','entries':out,'A_end_sha256':previous,
            'B_end_sha256':digest([e['B_relay_sha256'] for e in out]),
            'native_BV_credit':0,'native_learning':False}


def receive(b):
    need(type(b) is dict and set(b)=={'stage','entries','A_end_sha256','B_end_sha256','native_BV_credit','native_learning'} and b['stage']=='B','BAD_B_DOC')
    need(b['native_BV_credit']==0 and b['native_learning'] is False,'BAD_B_PROMOTION')
    entries=b['entries'];need(type(entries) is list and len(entries)==24,'C_PACKET_COUNT')
    # Reconstruct A chain from only B-owned data and ensure untouched relay.
    parsed=[];previous='0'*64;last_idx=-1
    for i,e in enumerate(entries):
        need(type(e) is dict and set(e)=={'a_entry','B_relay_sha256'},'B_ENTRY_SCHEMA')
        a=e['a_entry'];need(type(a) is dict and set(a)=={'packet','previous','A_entry_sha256'},'A_ENTRY_SCHEMA')
        row=a['packet'];valid_packet(row,i)
        need(row['case_index']>last_idx,'C_REPLAY_OR_OUT_OF_ORDER')
        last_idx=row['case_index']
        need(a['previous']==previous,'C_A_CHAIN_BROKEN')
        sha=digest({'packet':row,'previous':previous})
        need(a['A_entry_sha256']==sha,'C_A_SHA_INVALID')
        need(e['B_relay_sha256']==digest({'A_entry_sha256':sha,'B_seq':i}),'C_B_SHA_INVALID')
        previous=sha;parsed.append(row)
    need(b['A_end_sha256']==previous and b['B_end_sha256']==digest([e['B_relay_sha256'] for e in entries]),'C_TERMINAL_DRIFT')
    return {'stage':'C','received':len(parsed),'research_feedback_outcomes':{k:sum(e['a_outcome']==k for e in parsed) for k in ('IMPROVED','UNCHANGED','WORSENED')},
           'research_feedback_sha256':digest(parsed),'A_end_sha256':previous,'B_end_sha256':b['B_end_sha256'],
           'C_native_credit_applied':0,'C_native_learning_steps':0,'authenticated_A_measurement':False,
           'native_C_authority':False,'promotion_allowed':False}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--role',required=True,choices=['A','B','C'])
    parser.add_argument('--input',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    try:
        need(args.input.is_file() and not args.input.is_symlink(),'INPUT_FILE_INVALID')
        need(not args.output.exists(),'OUTPUT_EXISTS')
        data=json.loads(args.input.read_bytes())
        value={'A':issue,'B':relay,'C':receive}[args.role](data)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_bytes((json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode())
        print('SPK RESEARCH FEEDBACK',args.role,'PASS','NO NATIVE BV OR LEARNING')
    except (CausalBoundary,ValueError,KeyError,TypeError,OSError) as ex:
        raise SystemExit('T5VWX FAIL CLOSED: '+str(ex))

if __name__=='__main__':main()
