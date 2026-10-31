"""T7JKL/MNO/PQR cumulative: bound semantic overlay + durable research P-intent.

Uses original frozen BV scheduler for full on-fwork trials. No promotion to
native semantic BV, SPK Memory Contract authorization, or trusted learning.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,tempfile
from pathlib import Path
from research.spk_v5_t6abc_def_ghi.loop_v0 import digest
from research.spk_v5_t7abc_def_ghi.epoch_state_v0 import EpochState
from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import BridgeRejected,check
from .semantic_custody_v0 import compose,verify
from .p_intent_v0 import prepare,settle
from .native_epoch_v0 import execute_raw

SCHEMA='spk-v5-t7jkl-mno-pqr-bv-semantic-custody-and-P-intent/research-v0'
REFERENCE_SHA='1d44f2884eb565c318e963ed06e6752e90f496ad01b6fc30bceb52183160a1b2'
PE_SHA='8e9d08ddc165e0c6e307ca16cc849feb7eabad33c148c26f4faa436c890d752c'
BV_SHA='2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def episode(store,cue,goal,*,drop_forward=False):
    issue=store.issue(cue,goal)
    source,checked=execute_raw(issue['choice'],goal,drop_forward=drop_forward)
    packet=compose(source,issue,drop_forward=drop_forward)
    intent=prepare(source,issue,packet,drop_forward=drop_forward)
    settlement=settle(store,source,issue,packet,intent,drop_forward=drop_forward)
    return {'issue':issue,'source_sha256':checked['source_sha256'],
            'A_outcome':checked['A_outcome'],'semantic_chain_sha256':digest(packet),
            'P_intent_sha256':digest(intent),'C_updated':settlement['updated'],
            'structural_BV_C':checked['reverse_A_B_C'],'raw_BV_semantic_field_added':False,
            'native_P_write':False}

def trial(*,learn,drop=False,phases=4):
    with tempfile.TemporaryDirectory(prefix='spk-t7jkl-mno-') as d:
        store=EpochState(Path(d)/'P.sqlite',learn=learn)
        rows=[]
        for phase in range(phases):
            for n in range(24):
                cue=n%2
                goal=(11 if cue==0 else 12) if phase%2==0 else (12 if cue==0 else 11)
                row=episode(store,cue,goal,drop_forward=drop)
                rows.append(row)
                if n in (11,23):store.reopen()
        audit=store.audit();store.close()
    return {'episodes':len(rows),'successes':sum(r['A_outcome']=='IMPROVED' for r in rows),
      'P_updates':audit['updates'],'P_final':audit['policy'],'P_versions':audit['versions'],
      'raw_bv_calls':len(rows),'forward_deliveries':sum(r['structural_BV_C'] for r in rows),
      'receipt_rows_sha256':digest([r['semantic_chain_sha256'] for r in rows]),
      'intents_sha256':digest([r['P_intent_sha256'] for r in rows]),
      'source_sha256':digest([r['source_sha256'] for r in rows]),
      'full_rows_sha256':digest(rows),'durable_audit':audit}

def recover_once():
    with tempfile.TemporaryDirectory(prefix='spk-t7jkl-recovery-') as d:
        path=Path(d)/'P.sqlite';s=EpochState(path)
        issued=s.issue(0,11)
        source,verified=execute_raw(issued['choice'],issued['goal'])
        packet=compose(source,issued);intent=prepare(source,issued,packet)
        s.close();s=EpochState(path,create=False)
        check(s.unsettled()==[issued],'ISSUE_LOST_ACROSS_RECOVERY')
        out=settle(s,source,issued,packet,intent)
        check(out['updated'] is True,'RECOVERY_FAILED_TO_UPDATE')
        s.reopen()
        try:settle(s,source,issued,packet,intent)
        except BridgeRejected as err:check(str(err)=='STALE_OR_FORGED_ISSUE','REPLAY_REJECT_DRIFT')
        else:raise BridgeRejected('DOUBLE_COMMIT')
        audit=s.audit();s.close()
        check(audit['updates']==1 and audit['pending']==0,'LEDGER_RECOVERY')
        return {'reopen_before_vote':True,'one_commit':True,'replay_denied':True,
                'P_version_after_recover':audit['versions']['0'] if '0' in audit['versions'] else audit['versions'][0]}

def hostile_counterexample():
    """Host produces a coherent fake scheduler source (zero actual scheduler calls).

    The stronger hash-bound sidecar cannot prevent forgery of its trust root.
    This counterexample MUST stay a success, to prevent false native promotions.
    """
    from research.spk_v5_t7abc_def_ghi.tests.test_epoch_bridge import fake_source
    with tempfile.TemporaryDirectory(prefix='spk-t7jkl-forgery-') as d:
        store=EpochState(Path(d)/'P.sqlite')
        issued=store.issue(0,11)
        fake=fake_source(12,11)
        packet=compose(fake,issued)
        intent=prepare(fake,issued,packet)
        result=settle(store,fake,issued,packet,intent)
        audit=store.audit();store.close()
    check(result['updated'] and audit['updates']==1,'HOST_FORGERY_WITNESS_FAILED')
    return {'host_generated_coherent_fake_raw_scheduler_report':True,
            'new_original_scheduler_calls':0,'forged_A_B_C_semantic_custody_accepted':True,
            'forged_research_P_intent_committed':True,'native_attestation':False}

def run(root):
    root=Path(root)
    ref=root/'research/spk_v5_t7jkl_mno_pqr/reference/t7abc-def-ghi.json'
    check(sha(ref)==REFERENCE_SHA,'REFERENCE_T7_DRIFT')
    check(sha(root/'spk_architecture_v1/pe_execution_v1b.py')==PE_SHA,'FROZEN_PE_DRIFT')
    check(sha(root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA,'FROZEN_BV_DRIFT')
    control=trial(learn=False)
    adaptive=trial(learn=True)
    missing=trial(learn=True,drop=True,phases=1)
    recovery=recover_once()
    forgery=hostile_counterexample()
    prior=json.loads(ref.read_bytes())
    check(control['successes']==prior['T7ABC']['control_96']['successful_A_assessments']==48,'CONTROL_PARITY')
    check(adaptive['successes']==prior['T7ABC']['adaptive_96']['successful_A_assessments']==88,'ADAPTIVE_PARITY')
    check(adaptive['P_updates']==prior['T7ABC']['adaptive_96']['P_updates']==8,'P_UPDATE_PARITY')
    check(adaptive['P_final']=={str(k):v for k,v in prior['T7ABC']['adaptive_96']['P_final'].items()} or adaptive['P_final']=={int(k):v for k,v in prior['T7ABC']['adaptive_96']['P_final'].items()},'P_FINAL_PARITY')
    check(missing['forward_deliveries']==0 and missing['P_updates']==0,'MISSING_STRUCTURAL_CREDIT')
    return {'schema':SCHEMA,'status':'FROZEN_BV_STRUCTURAL_SEMANTIC_OVERLAY_WITH_RESEARCH_P_INTENT_ONLY',
        'T7JKL':{'semantic_bound_to_A_PE_emission':True,'native_BV_packet_semantic':False,
                 'original_frozen_scheduler_calls':control['raw_bv_calls']+adaptive['raw_bv_calls']+missing['raw_bv_calls']+1,
                 'A_B_C_semantic_overlay_only':True,'control_96':control,'adaptive_96':adaptive},
        'T7MNO':{'research_P_intent_version_bound':True,'research_P_intent_owner':'C',
                 'research_P_intent_domain':'P','native_memory_contract_admission':False,
                 'persisted_model_improvement':adaptive['successes']-control['successes'],
                 'restart_once_and_replay_reject':recovery,'full_source_PE_BV_used':True},
        'T7PQR':{'dropped_forward_24':missing,'privileged_host_full_source_rebinding':forgery,
                 'native_BV_credit':0,'native_learning':False},
        'source_T7_reference_sha256':REFERENCE_SHA,'frozen_PE_sha256':PE_SHA,
        'frozen_BV_sha256':BV_SHA,'original_source_pins':12,
        'A_sensor_authenticated':False,'C_source_authenticated':False,
        'host_can_forge':True,'native_P_state_modified':False,'native_BV_credit':0,
        'native_learning':False,'promotion_allowed':False,
        'limits':['Frozen BV-v0e transports only structural A-B-C deliveries, not A 21/22 verdict',
                  'Shadow semantic capsule joins host-visible A PE channel with frozen structural path; not native BV semantics',
                  'P-write intent is checked and committed by host SQLite research adapter, NOT native Memory Contract or PE P',
                  'All goals, per-epoch programs and A observations remain synthetic and host-authored',
                  'A privileged host can provide a fully forged source-looking report and coherent semantic custody without calling BV',
                  'No native causal learning, authenticated sensors, trusted source, or frozen contract edits']}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--out',required=True)
    args=ap.parse_args();p=Path(args.out)
    check(not p.exists() and not p.is_symlink(),'OUTPUT_EXISTS')
    r=run(args.root)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes((json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())
    print('T7JKL/MNO/PQR SEMANTIC CUSTODY AND RESEARCH P-INTENT PASS; NATIVE BV STRUCTURAL ONLY; HOST FORGEABLE; NO NATIVE LEARNING')
    print('report_sha256',sha(p))
if __name__=='__main__':main()
