"""T8 cumulative: SPECIFICATION CANDIDATE, runnable shadow compatibility, zero native grants.

Replays authentic frozen BV-v0e only on full fwork checkout. No frozen edits.
"""
from __future__ import annotations
import argparse,hashlib,json,tempfile
from pathlib import Path
from research.spk_v5_t7abc_def_ghi.epoch_state_v0 import EpochState
from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import check,verify_source
from research.spk_v5_t7abc_def_ghi.tests.test_epoch_bridge import fake_source
from research.spk_v5_t7jkl_mno_pqr.native_epoch_v0 import execute_raw
from .semantic_packet_v1_candidate import make_packet,verify_packet
from .p_admission_v1_candidate import evaluate,settle_research
from .epoch_port_v1_candidate import trial

SCHEMA='spk-v5-t8abc-def-ghi-semantic-P-candidate-contract/research-v0'
T7_REF_SHA='9044d665e4b56dbf1d3b58facb175248d294c05343182c095b1cd7440beb01ce'
PE_SHA='8e9d08ddc165e0c6e307ca16cc849feb7eabad33c148c26f4faa436c890d752c'
BV_SHA='2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hostile_model_witness():
    """Model-only attempt: host-synthesized raw BV-looking source, no scheduler run."""
    with tempfile.TemporaryDirectory(prefix='spk-t8-host-') as d:
        store=EpochState(Path(d)/'P.sqlite')
        issued=store.issue(0,11)
        fake=fake_source(12,11)
        pkt=make_packet(fake,issued)
        grant=evaluate(fake,issued,pkt)
        check(grant['native_grant'] is None,'FORGED_NATIVE_GRANT')
        receipt=settle_research(store,fake,issued,pkt,grant)
        state=store.audit();store.close()
    check(receipt['updated'] and state['updates']==1,'FORGERY_NOT_REPRODUCED')
    return {'host_fabricated_source_accepted_by_shadow_adapter':True,
            'new_real_scheduler_calls':0,'research_P_changed':True,
            'native_P_changed':False,'native_grant_issued':False,
            'native_origin_authenticated':False}


def recovery_witness():
    with tempfile.TemporaryDirectory(prefix='spk-t8-recover-') as d:
        store=EpochState(Path(d)/'P.sqlite')
        issued=store.issue(0,11)
        # Stubbed source is a unit of RESEARCH contract recovery, not a native source.
        source=fake_source(12,11)
        packet=make_packet(source,issued);admission=evaluate(source,issued,packet)
        store.reopen()
        assert store.unsettled()==[issued]
        commit=settle_research(store,source,issued,packet,admission)
        store.reopen()
        from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import BridgeRejected
        try:settle_research(store,source,issued,packet,admission)
        except BridgeRejected as e:check(str(e)=='STALE_OR_FORGED_ISSUE','REPLAY_REJECT_REASON_DRIFT')
        else:raise BridgeRejected('DUPLICATE_COMMIT')
        state=store.audit();store.close()
    check(commit['updated'] and state['updates']==1,'RECOVERY_COMMIT_COUNT')
    return {'pending_decision_survived_restart':True,
            'settled_once':True,'replay_after_reopen_denied':True,
            'native_P_written':False}


def run(root):
    root=Path(root)
    ref=root/'research/spk_v5_t8abc_def_ghi/reference/t7jkl-mno-pqr.json'
    check(sha(ref)==T7_REF_SHA,'REFERENCE_T7JKL_DRIFT')
    check(sha(root/'spk_architecture_v1/pe_execution_v1b.py')==PE_SHA,'FROZEN_PE_DRIFT')
    check(sha(root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA,'FROZEN_BV_DRIFT')
    historical=json.loads(ref.read_bytes())
    control=trial(learn=False)
    adaptive=trial(learn=True)
    drop=trial(learn=True,phases=1,drop=True)
    forgery=hostile_model_witness()
    recovery=recovery_witness()
    check(control['successes']==historical['T7JKL']['control_96']['successes']==48,'CONTROL_PARITY')
    check(adaptive['successes']==historical['T7JKL']['adaptive_96']['successes']==88,'ADAPTIVE_PARITY')
    check(adaptive['updates']==historical['T7JKL']['adaptive_96']['P_updates']==8,'UPDATE_PARITY')
    check(drop['successes']==0 and drop['updates']==0 and drop['semantic_packet_count']==0,'DROP_PARITY')
    check(control['semantic_packet_count']==96 and adaptive['semantic_packet_count']==96,'SEMANTIC_MSG_COUNT')
    check(not any((x['native_grants'],x['native_semantic_BV_deliveries'],x['native_P_writes']) != (0,0,0) for x in (control,adaptive,drop)),'FALSE_NATIVE_ADOPTION')
    return {'schema':SCHEMA,
            'status':'CANDIDATE_V1_SEMANTIC_PACKET_AND_P_ADMISSION_DRY_RUN_NO_NATIVE_ADOPTION',
            'T8ABC':{'v1_candidate_packet_generated':True,
                     'v0e_native_packets_have_semantic_payload':False,
                     'semantic_messages_in_adaptive_shadow_epochs':adaptive['semantic_packet_count'],
                     'A_semantic_source':'separate original PE emission 21/22',
                     'source_transport':'original BV v0e structural A-B-C',
                     'research_packet_only':True},
            'T8DEF':{'proposed_P_owner':'C','proposed_P_domain':'P','proposed_mode':'execute',
                     'native_memory_contract_admission':'DENIED_NO_NATIVE_MEMORY_CONTRACT_GRANT',
                     'native_admission_success_count':0,'model_P_updates':adaptive['updates'],
                     'native_P_updates':0,'research_P_recovery':recovery},
            'T8GHI':{'baseline_96':control,'adaptive_96':adaptive,
                     'dropped_forward_24':drop,'privileged_host_counterexample':forgery,
                     'model_success_delta':adaptive['successes']-control['successes']},
            'original_scheduler_calls':control['episodes']+adaptive['episodes']+drop['episodes'],
            'prior_T7JKL_report_sha256':T7_REF_SHA,
            'frozen_PE_sha256':PE_SHA,'frozen_BV_sha256':BV_SHA,
            'original_source_pins':12,'original_frozen_code_unchanged':True,
            'A_sensor_authenticated':False,'C_source_authenticated':False,
            'host_can_forge':True,'native_semantic_BV_credit':0,
            'native_P_state_modified':False,'native_learning':False,
            'promotion_allowed':False,
            'limits':['Candidate v1 message is built by host after V0e; native V0e packets remain structural',
                'No real SPK Memory Contract authorization call exists: native grant always DENIED',
                'Host-managed research SQLite C-state is updated; genuine SPK P state is untouched',
                'A goals and episodes remain host-authored synthetic, without trusted physical causal observations',
                'Host can synthesize a coherent BV-looking report to update research P without a scheduler call',
                'Full native learning needs a versioned runtime API and native P write transaction with independent authority']}


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True)
    arg=p.parse_args();out=Path(arg.out)
    check(not out.exists() and not out.is_symlink(),'OUTPUT_EXISTS')
    report=run(arg.root)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes((json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())
    print('T8ABC/DEF/GHI CUMULATIVE V1 CANDIDATE SEMANTIC AND P ADMISSION RESEARCH PASS; NO NATIVE BV OR LEARNING')
    print('reference_report_sha256',sha(out))
if __name__=='__main__':main()
