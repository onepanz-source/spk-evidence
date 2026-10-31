"""T5MNO: A-local observational evaluation, no independent trusted sensor.

Deliberately does not infer C action efficacy from correlated observations.
Contradiction/counterfactual tests prove A outcome is not an echo of C sign;
attestation and causal-effect claims remain false.
"""
from __future__ import annotations
import argparse,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
from collections import Counter
from .a_local_outcome_v0 import require,synthetic_A_observation,evaluate_observation
from .a_receiver_process_v0 import digest,canonical
from research.spk_v5_t5jkl import t5jkl

SCHEMA='spk-v5-t5mno-a-local-outcome-and-noncausal-judgment/research-v0'
STATUS='A_LOCAL_JUDGMENT_STRUCTURAL_NOT_SENSOR_AUTHENTICATED_OR_CAUSAL'
T5JKL_SHA='6967fb45f7d612b0e7297e30e0c16a1e47650614988cf1530748bd958a5271c8'

def sha_file(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def audit(root,full_source_pins=True):
    root=Path(root)
    # Previous offline report and all frozen-source pins must be untouched.
    pins=t5jkl.custody(root,full_source_pins)
    j=t5jkl.pinned(root/'research/spk_v5_t5mno/reference/t5jkl-receiver-independence.json',T5JKL_SHA,'T5JKL')
    require(j['cases']==180 and j['promotion_allowed'] is False and
        j['classification_counts']['fresh_received']==72 and
        j['A_independent_judgments_authenticated']==0,'T5JKL_REFERENCE_INVALID')
    require(pins['original_source_pins']==12,'TWELVE_PINS_REQUIRED')
    inbound=[{'case_index':row['index'],'source_sha256':row['source_sha256'],
              'receipt_present':row['A_fresh_receipt']} for row in j['rows']]
    # Separate Python process A, allowed only the stripped inbound. Its own local
    # measurement profile is not sent through the host-to-A input pipe.
    with tempfile.TemporaryDirectory(prefix='spk-t5mno-') as folder:
        inpath=Path(folder)/'in.json';outpath=Path(folder)/'out.json'
        inpath.write_bytes(canonical(inbound))
        run=subprocess.run([sys.executable,'-m','research.spk_v5_t5mno.a_receiver_process_v0',
            '--input',str(inpath),'--out',str(outpath)],cwd=root,text=True,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
        require(run.returncode==0,'A_PROCESS_FAIL_'+str(run.returncode)+'_'+run.stderr[-250:])
        a=json.loads(outpath.read_bytes())
    require(a['schema']=='spk-v5-t5mno-A-local-outcome-process/research-v0' and len(a['rows'])==180,'A_PROCESS_INVALID')
    cnt=Counter();paired=Counter();both=Counter();coh=Counter()
    rows=[]
    # Compare pinned T5JKL cross-plane reference, but do not send its failure
    # flags or C sign to A. They remain an external audit plane only.
    t4ghi=t5jkl.pinned(root/'research/spk_v5_t5jkl/reference/t4ghi-one-pass-sign.json',t5jkl.T4GHI_SHA,'T4GHI')
    for old,received,native in zip(j['rows'],a['rows'],t4ghi['H_rows']):
        i=old['index'];require(received['case_index']==native['index']==i,'ROW_ORDER')
        require(received['source_sha256']==old['source_sha256'],'ROW_SOURCE_SHA')
        require(received['C_receipt_present']==old['A_fresh_receipt'],'RECEIPT_DRIFT')
        assert received['A_external_authenticated'] is False and received['native_credit'] is False
        outcome=received['A_outcome'];cnt[outcome]+=1
        if received['C_receipt_present']:
            paired[outcome]+=1
            sign=native['C_sign_candidate_from_same_source_forward_output']
            require(sign in (-1,1),'C_SIGN_MISSING')
            both[(outcome,sign)]+=1
            coh[old['classification']]+=1
        require(received['A_causally_attributed_to_C'] is False,'FALSE_C_CAUSAL_CLAIM')
        rows.append({'index':i,'A_outcome':outcome,'A_assessment':received['A_structural_assessment'],
            'A_observation_sha256':received['A_local_observation_sha256'],
            'receipt_present':received['C_receipt_present'],
            'source_sha256':old['source_sha256'],'research_guard_candidate':old['research_guard_candidate'],
            'source_forward_emission_chain':old['source_forward_emission_chain'],
            'A_independent_observation_authenticated':False,
            'A_to_C_credit':False,'A_causal_attribution_to_C':False})
    require(dict(cnt)=={'IMPROVED':60,'WORSENED':60,'UNCHANGED':60},'LOCAL_OBSERVATION_COUNTS')
    require(dict(paired)=={'IMPROVED':24,'WORSENED':24,'UNCHANGED':24},'LOCAL_PAIRED_COUNTS')
    require(all(both[(o,s)]==12 for o in ('IMPROVED','WORSENED','UNCHANGED') for s in (-1,1)),'C_SIGN_DECORRELATION')
    require(coh=={'FRESH_RECEIPT_GUARD_CANDIDATE':24,'FRESH_RECEIPT_WITH_SOURCE_FAULT':48},'RECEIPT_CLASS_DRIFT')
    mismatch=sum(1 for item in rows if item['receipt_present'] and not item['source_forward_emission_chain'])
    require(mismatch==24,'FROZEN_FORWARD_EMISSION_MISMATCH')
    # Same C packet would yield three mutually incompatible judgments upon changing
    # the synthetic A measurement; not evidence C caused the A outcome.
    original=synthetic_A_observation(0)
    cf={label:evaluate_observation({**original,'after':after})['outcome'] for label,after in
        (('improve',8),('worsen',4),('unchanged',6))}
    require(cf=={'improve':'IMPROVED','worsen':'WORSENED','unchanged':'UNCHANGED'},'COUNTERFACTUAL_FAIL')
    # Host replacing a local A observation is also able to change the judgment:
    # real sensor provenance and attribution remain unproven.
    need_forgery=(evaluate_observation({**original,'after':4})['assessment']==-1)
    require(need_forgery,'HOST_SENSOR_FORGERY_MISSING')
    require(t5jkl.custody(root,full_source_pins)==pins,'CUSTODY_CHANGED')
    return {'schema':SCHEMA,'status':STATUS,'T5JKL_reference_sha256':T5JKL_SHA,
        'cases':180,'A_separate_process':True,'A_local_synthetic_observations':180,
        'A_local_structural_judgments':180,'A_paired_research_outcomes':72,
        'A_local_outcomes':dict(sorted(cnt.items())),
        'paired_outcomes':dict(sorted(paired.items())),
        'C_sign_cross_tab':[{'A_outcome':o,'C_sign':s,'count':both[(o,s)]} for o in ('IMPROVED','WORSENED','UNCHANGED') for s in (-1,1)],
        'A_research_guard_candidates':24,'A_source_fault_receipts':48,
        'A_paired_without_frozen_emission_chain':mismatch,
        'counterfactual_fixed_C_receipt_A_local_observation_changed':cf,
        'host_can_forge_A_measurement':need_forgery,
        'host_can_forge_C_result':True,
        'A_sensor_source_authenticated':False,'A_C_causal_attribution_proven':False,
        'native_C_authenticated':False,'native_BV_credit':0,'native_learning':False,
        'promotion_allowed':False,'new_PE_calls':0,'new_frozen_scheduler_calls':0,
        'pins':pins,'rows_sha256':digest(rows),'rows':rows,
        'limits':['The A-local measurement policy and synthetic values are owned by a host-controlled Python process, NOT an independently attested physical sensor',
                  'The host-to-A input carries only case IDs, source hashes and receipt booleans; not C signs, failure flags, A goals or A measurements',
                  'A-local improvement/worsening is not a causal judgment that C caused the observed result',
                  'The host can rewrite A measurements as well as rebind old C results; there is no independent trusted authority',
                  'No native semantic BV credit, sender attestation or learning']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    v=p.parse_args()
    try:
        require(not v.out.exists(),'OUTPUT_EXISTS')
        doc=audit(v.root,True)
        v.out.parent.mkdir(parents=True,exist_ok=True)
        v.out.write_bytes((json.dumps(doc,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())
        print('T5MNO',STATUS,'A LOCAL',doc['A_local_synthetic_observations'],
              'PAIRED',doc['A_paired_research_outcomes'],'HOST A FORGERY',doc['host_can_forge_A_measurement'])
        print('SHA256',sha_file(v.out))
    except (ValueError,KeyError,AssertionError,TypeError,OSError,subprocess.TimeoutExpired) as exc:
        raise SystemExit('T5MNO FAIL CLOSED: '+str(exc))
if __name__=='__main__':main()
