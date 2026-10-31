"""T7ABC/DEF/GHI: execute source BV-v0e per epoch; external durable adaptive P.

One A receiver within frozen three-neuron BV constraint. No distributed
multi-receiver native learning or authenticated A goal/measurement claimed.
"""
from __future__ import annotations
import argparse,hashlib,json,tempfile
from pathlib import Path
from .scheduler_bridge_v0 import execute_episode,verify_source,BridgeRejected,check
from .epoch_state_v0 import EpochState
from research.spk_v5_t6abc_def_ghi.loop_v0 import digest

SCHEMA='spk-v5-t7abc-def-ghi-frozen-bv-epoch-bridge/research-v0'
PRIOR_SHA='4d5115384c480117e087cb63a7e5d8e6334f9de02557116572904b63d3ac0922'
PE_SHA='8e9d08ddc165e0c6e307ca16cc849feb7eabad33c148c26f4faa436c890d752c'
BV_SHA='2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9'


def sha_file(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def trial(*,learn:bool,phases:int=4,drop:bool=False):
    check(type(learn) is bool and type(phases) is int and 1<=phases<=4,'TRIAL_ARGUMENTS')
    check(type(drop) is bool,'DROP_ARGUMENT')
    with tempfile.TemporaryDirectory(prefix='spk-t7-bv-epochs-') as d:
        path=Path(d)/'P_C.sqlite'
        store=EpochState(path,learn=learn)
        traces=[];raw_a=[]
        for phase in range(phases):
            for idx in range(24):
                cue=idx%2
                target=(11 if cue==0 else 12) if phase%2==0 else (12 if cue==0 else 11)
                issue=store.issue(cue,target)
                report=execute_episode(issue['choice'],target,drop_forward=drop)
                settlement=store.settle(issue,report)
                traces.append({'phase':phase,'idx':idx,'cue':cue,'goal':target,'C_choice':issue['choice'],
                    'A_result':report['A_outcome'],'A_emission':report['A_emission'],
                    'source_sha256':report['source_sha256'],'C_updated':settlement['updated'],
                    'A_B_C_structural_BV':report['reverse_A_B_C'],'policy_version':issue['version']})
                raw_a.append(report['A_emission'])
                if idx in (11,23):store.reopen()
        audit=store.audit()
        check(audit['pending']==0 and audit['episodes']==len(traces),'UNSETTLED_EPOCH')
        check(store.updates==sum(r['C_updated'] for r in traces),'LEDGER_UPDATE_PARITY')
        result={'episodes':len(traces),'phases':phases,'learn':learn,'forward_drop':drop,
            'successful_A_assessments':sum(r['A_result']=='IMPROVED' for r in traces),
            'failed_A_assessments':sum(r['A_result']=='WORSENED' for r in traces),
            'structural_BV_C_deliveries':sum(r['A_B_C_structural_BV'] for r in traces),
            'P_updates':store.updates,'P_versions':store.versions,'P_final':store.table,
            'reopen_every_12_episodes':True,'source_results_sha256':digest([r['source_sha256'] for r in traces]),
            'trace_sha256':digest(traces),'A_channels_sha256':digest(raw_a),
            'audit':audit,'first_six':traces[:6]}
        store.close()
    return result

def crash_recovery_with_actual_scheduler():
    with tempfile.TemporaryDirectory(prefix='spk-t7-crash-') as d:
        path=Path(d)/'owner-C.sqlite'
        s=EpochState(path,learn=True)
        issue=s.issue(0,11);s.close()
        s=EpochState(path,learn=True,create=False)
        check(s.unsettled()==[issue],'PENDING_RECOVERY_DRIFT')
        evidence=execute_episode(issue['choice'],issue['goal'])
        result=s.settle(issue,evidence)
        check(result['updated'] is True,'RECOVERED_C_NOT_UPDATED')
        s.reopen()
        try:s.settle(issue,evidence)
        except BridgeRejected as err:check(str(err)=='STALE_OR_FORGED_ISSUE','UNEXPECTED_REPLAY_REJECTION')
        else:raise BridgeRejected('DOUBLE_APPLY_AFTER_REOPEN')
        audit=s.audit();s.close()
    return {'pending_reopened_and_settled':True,'duplicate_after_reopen_rejected':True,
            'one_update_after_reopen':audit['updates']==1,'audit_after_reopen':audit}

def privileged_host_forgery_counterexample():
    """The adapter trusts source-looking evidence, so an omnipotent host can forge.

    The fabricated SHA is NOT a genuine frozen BV output. This test proves the
    external state adapter cannot independently authenticate that assertion.
    """
    forged={'C_choice':12,'A_outcome':'WORSENED','A_emission':22,'C_B_A':True,
        'reverse_A_B_C':True,'full_BV_scheduler':True,'eligible_to_update':True,
        'source_sha256':'f'*64,'source_batches':3,'source_bv_deliveries':2}
    with tempfile.TemporaryDirectory(prefix='spk-t7-forgery-') as d:
        s=EpochState(Path(d)/'P.sqlite',learn=True)
        issue=s.issue(0,11)
        # Bypasses verify_source just as a privileged host can patch the adapter.
        admitted=s.settle(issue,forged)
        check(admitted['updated'] and s.table[0]==11,'EXPECTED_HOST_IMPERSONATION_FAILED')
        s.close()
    return {'host_bypassed_producer_verification':True,'host_forged_ledger_accepted':True,
            'native_sender_authentication':False}

def run(root):
    root=Path(root).resolve()
    # The manifest gate verifies all source bytes/pins before invoking this.
    prior=root/'research/spk_v5_t7abc_def_ghi/reference/t6stu-vwx-yza-cumulative.json'
    check(sha_file(prior)==PRIOR_SHA,'ANCESTRAL_REPORT_SHA_DRIFT')
    check(sha_file(root/'spk_architecture_v1/pe_execution_v1b.py')==PE_SHA,'FROZEN_PE_DRIFT')
    check(sha_file(root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA,'FROZEN_BV_DRIFT')
    control=trial(learn=False)
    adaptive=trial(learn=True)
    legacy_48_control=trial(learn=False,phases=2) # 48 episodes, one goal switch
    legacy_48_adaptive=trial(learn=True,phases=2)
    # To isolate a stationary task, trial below uses a single 24-episode regime.
    stationary_control=trial(learn=False,phases=1)
    stationary_adaptive=trial(learn=True,phases=1)
    missing=trial(learn=True,phases=1,drop=True)
    crash=crash_recovery_with_actual_scheduler()
    attacker=privileged_host_forgery_counterexample()
    # First principles not 'expected success=80': run the actual source scheduler.
    check(control['episodes']==96 and adaptive['episodes']==96,'EPISODE_COVERAGE')
    check(control['successful_A_assessments']==48 and adaptive['successful_A_assessments']==88,
        'FROZEN_SCHEDULER_FUNCTIONAL_LEARNING_DRIFT')
    check(adaptive['P_updates']==8 and control['P_updates']==0,'FROZEN_SCHEDULER_P_ADAPTATION_DRIFT')
    check(stationary_adaptive['successful_A_assessments']==22 and stationary_control['successful_A_assessments']==0,'STATIONARY_CONDITION_DRIFT')
    check(missing['successful_A_assessments']==0 and missing['P_updates']==0 and missing['structural_BV_C_deliveries']==0,
        'MISSING_FORWARD_UNSAFELY_LEARNED')
    check(all(x['structural_BV_C_deliveries']==x['episodes'] for x in
              (control,adaptive,stationary_control,stationary_adaptive)), 'FROZEN_BV_RETURN_MISSING')
    return {'schema':SCHEMA,'status':'FULL_FROZEN_BV_EPOCHS_WITH_HOST_OWNED_P_ADAPTATION_RESEARCH_ONLY',
        'T7ABC':{'genuine_frozen_BV_executions':sum(x['episodes'] for x in (control,adaptive,legacy_48_control,legacy_48_adaptive,stationary_control,stationary_adaptive,missing))+1,
            'three_node_bound':True,'source_scheduler_function':'execute_live_v0e',
            'same_epoch_A_terminal_assessment_and_C_receipt':True,
            'BV_packet_contains_A_semantic_verdict':False,'A_emits_semantic_output_separately':True,
            'control_96':{k:v for k,v in control.items() if k not in ('first_six',)},
            'adaptive_96':{k:v for k,v in adaptive.items() if k not in ('first_six',)}},
        'T7DEF':{'persistent_host_owned_C_P':True,'atomic_settlements':True,
            'adaptive_improvement_96':adaptive['successful_A_assessments']-control['successful_A_assessments'],
            'stationary_24':{'control':stationary_control['successful_A_assessments'],
                             'adaptive':stationary_adaptive['successful_A_assessments']},
            'first_six_trained':adaptive['first_six'],'recover':crash},
        'T7GHI':{'lost_forward_24':{k:missing[k] for k in ('episodes','P_updates','structural_BV_C_deliveries','successful_A_assessments')},
            'host_forgery_witness':attacker,'A_goal_host_authored':True,
            'single_A_receiver_only':True,'former_T6_two_receiver_replay_not_promoted':True},
        'prior_T6_state_report_sha256':PRIOR_SHA,'frozen_PE_sha256':PE_SHA,
        'frozen_BV_sha256':BV_SHA,'original_source_pins':12,
        'native_C_authenticated':False,'A_sensor_authenticated':False,
        'native_P_state_modified':False,'native_BV_credit':0,'native_learning':False,
        'host_can_forge':True,'promotion_allowed':False,
        'limits':['Original frozen BV-v0e executes every host-authored three-node episode, but epochs are composed by a research driver',
                  'C selection uses host-managed SQLite P state and changes the admitted C instruction tuple between epochs, not frozen SPK P storage',
                  'A terminal channel 7 triggers native structural BV packets; A meaning (21/22) is read from a separate PE emission by host code',
                  'No authenticated A sensor/goal, no semantic verdict in frozen BV packet, no P-memory SPK authority transfer',
                  'Frozen BV v0e only admits 3 nodes, so T6 four-node A+D scenario remains separate',
                  'Host can falsify accepted evidence; no native learning or hardware causal authority']}

def write_once(path,value):
    p=Path(path)
    check(not p.exists() and not p.is_symlink(),'REPORT_EXISTS')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes((json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())

def main():
    a=argparse.ArgumentParser();a.add_argument('--root',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    x=a.parse_args()
    try:
        report=run(x.root)
        write_once(x.out,report)
        print('T7ABC/DEF/GHI RESEARCH EPOCH BRIDGE PASS; GENUINE BV-V0E SCHEDULER; EXTERNAL P; NO NATIVE BV OR LEARNING')
        print('report_sha256',sha_file(x.out))
    except (BridgeRejected,AssertionError,OSError,ValueError,KeyError,TypeError,RuntimeError) as e:
        raise SystemExit('T7ABC/DEF/GHI FAIL CLOSED: '+str(e))
if __name__=='__main__':main()
