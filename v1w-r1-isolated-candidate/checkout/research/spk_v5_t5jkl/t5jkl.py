"""T5JKL: cross-check T5GHI A freshness against T4GHI source observations.

Research only. ZERO new scheduler/PE runs, ZERO A independent evaluations.
Never promote native BV, learning, provenance authenticity, or sensor validity.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from .independence_contract_v0 import BoundaryViolation,need,classify

SCHEMA='spk-v5-t5jkl-receiver-independence-audit/research-v0'
STATUS='FRESH_RECEIPT_NOT_INDEPENDENT_A_JUDGMENT_OR_NATIVE_CREDIT'
T5GHI_SHA='f4296cdc55313967fcaab3f34810867128b2550ad85978e4a3f9196eb8028a86'
T4GHI_SHA='dc98a1a5e45270d665e5119540ae960e405f4d02b703bd0c52d04202873abef3'
T4ZABC_SHA='7de3ccc8c374212748ccedcbd1a4b3d4e99f116b9a6f39e0190695a746cf9d4c'

def digest(v): return sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha_file(p):return sha256(Path(p).read_bytes()).hexdigest()
def pinned(p,expected,name):
    need(Path(p).is_file() and not Path(p).is_symlink(),'MISSING_'+name)
    need(sha_file(p)==expected,'SHA_DRIFT_'+name)
    return json.loads(Path(p).read_bytes())

def custody(root,full_source_pins=True):
    from research.spk_v5_t5ghi import t5ghi
    r=Path(root)
    pins=t5ghi.custody(r)
    topo=pinned(r/'research/spk_v5_t5abc/reference/t4zabc-topology.json',T4ZABC_SHA,'T4ZABC_TOPOLOGY')
    source=topo['source_pins']; need(len(source)==12,'TWELVE_SOURCE_PINS_MISSING')
    if full_source_pins:
        for path,expected in sorted(source.items()):
            p=r/path
            need(p.is_file() and not p.is_symlink() and sha_file(p)==expected,'ORIGINAL_SOURCE_PIN_DRIFT_'+path)
    return {'T5GHI_reference_sha256':T5GHI_SHA,'T4GHI_reference_sha256':T4GHI_SHA,
            'T4ZABC_reference_sha256':T4ZABC_SHA,'original_source_pins':len(source),
            'frozen_PE_sha256':pins['frozen_PE_sha256'],'frozen_BV_sha256':pins['frozen_BV_sha256'],
            'challenge_fork_sha256':pins['challenge_fork_sha256']}

def audit(root,full_source_pins=True):
    root=Path(root); pins=custody(root,full_source_pins)
    g=pinned(root/'research/spk_v5_t5jkl/reference/t4ghi-one-pass-sign.json',T4GHI_SHA,'T4GHI')
    a=pinned(root/'research/spk_v5_t5jkl/reference/t5ghi-receiver-freshness.json',T5GHI_SHA,'T5GHI')
    need(g['promotion_allowed'] is False and a['promotion_allowed'] is False,'ANCESTOR_PROMOTION')
    need(a['host_can_forge_runtime'] is True and a['host_rebind_forgery_witness']['C_new_PE_computations']==0
         and a['host_rebind_forgery_witness']['fresh_challenge_accepted_by_A'] is True,'HOST_WITNESS_MISSING')
    need(a['A_receiver_process_stats']=={'issued':180,'accepted':72,'expired':108,'rejected':4},'A_STATS_DRIFT')
    need(a['all_180_source_and_T5DEF_port_sha_parity'] is True,'FROZEN_OUTPUT_DRIFT')
    srows=g['H_rows']; arows=a['rows']; need(len(srows)==len(arows)==180,'ROW_COUNT_DRIFT')
    rows=[]; totals=Counter(); crosstab=Counter()
    for i,(src,receive) in enumerate(zip(srows,arows)):
        need(src.get('index')==receive.get('index')==i,'ORDER_MISMATCH_'+str(i))
        res=classify(receive,src)
        totals[res['classification']]+=1
        if res['A_fresh_receipt']:totals['fresh_received']+=1
        if res['source_forward_emission_chain']:totals['source_chain_observed']+=1
        if res['research_guard_candidate']:totals['research_guard_candidates']+=1
        if res['A_fresh_receipt'] and not res['source_forward_emission_chain']:
            totals['fork_receipt_without_source_forward_emission_chain']+=1
        crosstab[(res['failure'],res['A_fresh_receipt'],res['source_forward_emission_chain'])]+=1
        rows.append(res)
    expected={'NO_SIGN_RECEIVED':108,'FRESH_RECEIPT_WITH_SOURCE_FAULT':48,
              'FRESH_RECEIPT_GUARD_CANDIDATE':24,'fresh_received':72,
              'source_chain_observed':48,'research_guard_candidates':24,
              'fork_receipt_without_source_forward_emission_chain':24}
    need(dict(totals)==expected,'CROSS_PLANE_COUNTS_DRIFT')
    need(crosstab[('none',True,True)]==24 and
         crosstab[('no_forward',True,True)]==24 and
         crosstab[('no_reverse',True,False)]==24 and
         sum(n for (f,acc,_),n in crosstab.items() if not acc)==108,'FAULT_TOPOLOGY_DRIFT')
    need(custody(root,full_source_pins)==pins,'CUSTODY_CHANGED_DURING_RUN')
    limits=['A challenge verified message freshness and continuity, NOT any independent assessment of C',
            '24 research guard candidates depend on host-visible source failure metadata, NOT independent A goals',
            '24 A fresh receipts under no_reverse have no coherent T4GHI forward.emissions C-B-A candidate; these evidence planes differ',
            'Even a self-declared independent A sensor would lack externally authenticated custody in this host-controlled Python runtime',
            'Privileged host replay/rebinding proves no source attestation; no native BV or learning promotion']
    return {'schema':SCHEMA,'status':STATUS,'T5GHI_report_sha256':T5GHI_SHA,
       'T4GHI_report_sha256':T4GHI_SHA,'source_pins':pins,
       'cases':len(rows),'new_original_scheduler_calls':0,'new_PE_compute_calls':0,
       'classification_counts':dict(sorted(totals.items())),
       'failure_context_counts':[{'failure':f,'fresh_received':acc,'source_forward_chain':coh,'count':n}
                                 for (f,acc,coh),n in sorted(crosstab.items())],
       'all_180_source_sha_parity':True,'A_independent_goal_observations':0,
       'A_independent_judgments_authenticated':0,'native_C_authenticated':False,
       'native_BV_credit':0,'native_learning':False,'promotion_allowed':False,
       'privileged_host_cached_rebind_succeeds':True,'rows_sha256':digest(rows),'rows':rows,'limits':limits}

def main():
    a=argparse.ArgumentParser();a.add_argument('--root',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    args=a.parse_args()
    try:
        need(not args.out.exists(),'OUTPUT_ALREADY_EXISTS')
        result=audit(args.root,True)
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_bytes((json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n').encode())
        print('T5JKL',STATUS,'fresh',result['classification_counts']['fresh_received'],
              'guard-only',result['classification_counts']['research_guard_candidates'],
              'A independent goals',result['A_independent_goal_observations'],'NATIVE CREDIT 0')
        print('SHA256',sha_file(args.out))
    except (BoundaryViolation,ValueError,KeyError,TypeError,OSError,ImportError,AssertionError) as exc:
        raise SystemExit('T5JKL FAIL CLOSED: '+str(exc))

if __name__=='__main__':main()
