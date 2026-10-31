"""T8JKL/MNO/PQR cumulative, one source-linked reference-v1 evidence report.

Live full acceptance requires unmodified PE and BV source plus genuine
admission dependencies from user's SPK repo. Local synthetic tests are NOT that.
"""
from __future__ import annotations
import argparse,json,hashlib,tempfile
from pathlib import Path
from research.spk_v5_t6abc_def_ghi.loop_v0 import digest
from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import check
from research.spk_v5_t7abc_def_ghi.tests.test_epoch_bridge import fake_source
from research.spk_v5_t8abc_def_ghi.cumulative_gate_v0 import PE_SHA,BV_SHA
from .runtime_v1_reference import trial
from .p_authority_v1 import PAuthorityV1
from .semantic_bus_v1 import dispatch

SCHEMA='spk-v5-t8jkl-mno-pqr-reference-v1-semantic-p-execution/research-v0'
REFERENCE_T8_SHA='ee90e32993a4a4a1de83376e155812f32d660c1fd51a8645af09d953c2a47b48'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def duplicate_and_recovery():
    with tempfile.TemporaryDirectory(prefix='spk-v1-p-recover-') as tmp:
        db=Path(tmp)/'P.sqlite';state=PAuthorityV1(db)
        d=state.issue(0,11);src=fake_source(12,11);pkt=dispatch(src,d)
        state.reopen()
        check(state.unsettled()==[d],'P_PENDING_NOT_DURABLE')
        result=state.settle(d,src,pkt)
        state.reopen();ok=False
        try:state.settle(d,src,pkt)
        except ValueError:ok=True
        check(ok,'P_REPLAY_AFTER_REOPEN')
        a=state.audit();state.close()
    check(result['P_written'] and a['reference_P_writes']==1,'P_COMMIT_AT_MOST_ONCE')
    return {'pending_durable':True,'replay_rejected':True,'grant_consumed_once':True,
       'reference_v1_grants':a['reference_grants'],'native_SPK_grants':0}


def host_forgery_witness():
    # This input is a *known fabrication*. It never called the frozen scheduler.
    with tempfile.TemporaryDirectory(prefix='spk-v1-host-forge-') as tmp:
        store=PAuthorityV1(Path(tmp)/'P.sqlite')
        d=store.issue(0,11);source=fake_source(12,11)
        packet=dispatch(source,d);result=store.settle(d,source,packet)
        a=store.audit();store.close()
    check(result['P_written'] and a['reference_grants']==1,'EXPECTED_UNTRUSTED_HOST_FORGERY')
    return {'scheduler_calls':0,'host_fake_source_accepted':True,
        'reference_v1_grant_forged':True,'native_SPK_grant_forged':False,
        'host_full_database_reseal_possible':True}


def report(root,*,source_executor=None):
    root=Path(root)
    ref=root/'research/spk_v5_t8jkl_mno_pqr/reference/t8abc-def-ghi.json'
    check(sha(ref)==REFERENCE_T8_SHA,'T8_PIN_DRIFT')
    check(sha(root/'spk_architecture_v1/pe_execution_v1b.py')==PE_SHA,'ORIGINAL_PE_DRIFT')
    check(sha(root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA,'ORIGINAL_BV_DRIFT')
    prior=json.loads(ref.read_bytes())
    base=trial(learn=False,source_executor=source_executor)
    adaptive=trial(learn=True,source_executor=source_executor)
    lost=trial(learn=True,phases=1,drop=True,source_executor=source_executor)
    recovered=duplicate_and_recovery()
    hostile=host_forgery_witness()
    check((base['successes'],adaptive['successes'],lost['successes'])==(48,88,0),'BASELINE_ADAPTATION_PARITY')
    check((base['reference_v1_P_grants'],adaptive['reference_v1_P_grants'],lost['reference_v1_P_grants'])==(0,8,0),'REFERENCE_GRANTS_PARITY')
    check((base['reference_v1_P_writes'],adaptive['reference_v1_P_writes'],lost['reference_v1_P_writes'])==(0,8,0),'REFERENCE_WRITES_PARITY')
    check((base['reference_v1_semantic_receipts'],adaptive['reference_v1_semantic_receipts'],lost['reference_v1_semantic_receipts'])==(96,96,0),'REFERENCE_DELIVERY_PARITY')
    check(base['source_rows_sha256']==prior['T8GHI']['baseline_96']['source_rows_digest'], 'FROZEN_BASELINE_SOURCE_DRIFT')
    check(adaptive['source_rows_sha256']==prior['T8GHI']['adaptive_96']['source_rows_digest'], 'FROZEN_ADAPTIVE_SOURCE_DRIFT')
    check(lost['source_rows_sha256']==prior['T8GHI']['dropped_forward_24']['source_rows_digest'], 'FROZEN_LOSS_SOURCE_DRIFT')
    return {'schema':SCHEMA,'status':'V1_REFERENCE_OWNED_SEMANTIC_BUS_AND_P_GRANTS_NOT_NATIVE_SPK',
        'T8JKL':{'reference_v1_semantic_payloads_carried':adaptive['reference_v1_semantic_receipts'],
          'new_v1_semantic_bus':True,'v0e_frozen_remains_structural':True,
          'verdict_from_original_A_PE_emission':True,
          'three_node_source_bound':True},
        'T8MNO':{'P_owner':'C','P_domain':'P','P_mode':'execute',
          'reference_v1_P_grants':adaptive['reference_v1_P_grants'],
          'reference_v1_P_commits':adaptive['reference_v1_P_writes'],
          'native_SPK_Memory_Contract_grants':0,
          'atomic_versioned_commit':True,'reopen_and_replay':recovered},
        'T8PQR':{'baseline_96':base,'adaptive_96':adaptive,'lost_forward_24':lost,
           'source_scheduler_calls':216 if source_executor is None else 0,
           'host_forgery_counterexample':hostile,'success_delta':40},
        'frozen_PE_sha256':PE_SHA,'frozen_BV_sha256':BV_SHA,
        'prior_T8_report_sha256':REFERENCE_T8_SHA,'original_source_pins':12,
        'A_sensor_authenticated':False,'C_source_authenticated':False,
        'host_can_forge':True,'native_BV_semantic_deliveries':0,
        'native_SPK_P_grants':0,'native_SPK_P_writes':0,'native_learning':False,
        'promotion_allowed':False,
        'limits':[
          'New semantic feedback is carried by a NEW reference-v1 event bus interpreting frozen BV outputs, not by BV-v0e native packets',
          'Reference-v1 P grants and writes exist in research runtime code; they are NOT native SPK Memory Contract admission',
          'Original frozen scheduler executes separate host-composed three-node epochs; no v1 integration into frozen tick loop',
          'A observations and goals are synthetic, host-authored and non-attested; source provenance cannot survive a privileged hostile host',
          'Positive performance evidence establishes only closed-loop causality in the controlled simulator, not native or real-world learning',
          'Host-synthesized source can obtain an internal reference grant without calling the original scheduler; native grant remains zero']}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();path=Path(args.out)
    check(not path.exists() and not path.is_symlink(),'REPORT_EXISTS')
    r=report(args.root)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+'\n')
    print('T8JKL/MNO/PQR V1 REFERENCE SEMANTIC BUS AND P AUTHORITY PASS; INTERNAL GRANTS ONLY; NO NATIVE BV OR LEARNING')
    print('reference_report_sha256',sha(path))
if __name__=='__main__':main()
