"""Cumulative frozen-source and Memory Contract surface readiness experiment."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import ensure,digest
from research.spk_v5_t8jkl_mno_pqr.cumulative_reference_gate import PE_SHA,BV_SHA
from research.spk_v5_t10jkl_mno_pqr.cumulative_resource_gate import report as old_report
from .surface_probe_v0 import probe,read_only_contract_request,reject_native_promotion
PARENT='789f8a13885caf0f2ae2ade81565916411b398c4686e21cb5e382db229cc20d1'
SCHEMA='spk-v5-t10stu-vwx-yza-native-memory-contract-readiness/research-v0'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def report(root):
    root=Path(root)
    p=root/'research/spk_v5_t10stu_vwx_yza/reference/t10jkl-mno-pqr-cumulative.json'
    ensure(sha(p)==PARENT,'PARENT_SHA_DRIFT')
    ensure(sha(root/'spk_architecture_v1/pe_execution_v1b.py')==PE_SHA,'ORIGINAL_PE_DRIFT')
    ensure(sha(root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA,'ORIGINAL_BV_DRIFT')
    old=json.loads(p.read_text())
    # Rerun prior algorithm and verify byte-exact reproduction of its evidence.
    fresh=old_report(root)
    ensure(json.dumps(fresh,sort_keys=True,indent=2,allow_nan=False)+'\n'==p.read_text(),
           'PREDECESSOR_BYTE_PARITY_FAILED')
    s=fresh['T10MNO']['scenarios']
    ensure([s[k]['successes'] for k in ('fixed_control','naive_three','context_affinity','serial')]==[48,84,88,88],
           'LEARNING_PARITY_DRIFT')
    ensure(all(s[k]['reference_grants']==s[k]['reference_P_writes']==8
               for k in ('naive_three','context_affinity','serial')),'REFERENCE_GRANT_DRIFT')
    actual=probe(root)
    req=read_only_contract_request(owner='C',domain='P',mode='execute',pe_id='PE-C-RESEARCH',context=0,version=4)
    p1=reject_native_promotion(req['request'])
    p2=reject_native_promotion(req['request'], {'issuer':'MEMORY_CONTRACT','grant':1,'native':True})
    ensure(not p1['promotion_allowed'] and not p2['promotion_allowed'] and
           p1['native_grants']==p2['native_grants']==0,'PROMOTION_TEST_FAILED')
    return {'schema':SCHEMA,'status':'READ_ONLY_NATIVE_MEMORY_CONTRACT_SURFACE_DISCOVERY_NO_BINDING',
        'T10STU':{'native_surface':actual,'original_PE_sha256':PE_SHA,'original_BV_sha256':BV_SHA,
                  'not_implemented_as_native_port':True},
        'T10VWX':{'typed_request':req,'reference_promotion_rejected':p1,
                   'host_claimed_native_promotion_rejected':p2,
                   'native_memory_contract_call_count':0,'native_grants':0,'native_P_writes':0},
        'T10YZA':{'prior_results':{k:{'successes':s[k]['successes'],
                  'waves':s[k]['waves'],'stale_vetoes':s[k]['stale_vetoes'],
                  'reference_grants':s[k]['reference_grants']}
                  for k in ('fixed_control','naive_three','context_affinity','serial','restarted_affinity')},
                  'prior_report_regenerated_byte_exact':True,
                  'native_adoption_blockers':['No authorized Memory Contract entrypoint was called',
                     'Source symbol discovery is not interface conformance',
                     'Unattested A observations and privileged host can forge',
                     'No native ownership or P transaction was executed']},
        'source_T10JKL_MNO_PQR_sha256':PARENT,'native_SPK_P_grants':0,
        'native_SPK_P_writes':0,'native_BV_semantic_deliveries':0,'native_learning':False,
        'host_can_forge':True,'promotion_allowed':False}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',default='.');ap.add_argument('--out',required=True);args=ap.parse_args()
    out=Path(args.out);ensure(not out.exists() and not out.is_symlink(),'REPORT_EXISTS')
    result=report(args.root);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n')
    print('T10STU/VWX/YZA READ-ONLY NATIVE MEMORY CONTRACT SURFACE READINESS PASS; NO NATIVE SPK GRANT OR LEARNING')
    print('reference_report_sha256',sha(out))
if __name__=='__main__':main()
