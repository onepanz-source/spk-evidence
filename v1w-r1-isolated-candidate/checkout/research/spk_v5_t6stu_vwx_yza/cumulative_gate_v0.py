"""T6STU/VWX/YZA: cumulative persisted owner-C state experiment gate.

Three sub-gates: transactional owned P state, byte-exact async/model parity
with forced database reopen, and adversarial/provenance limits. Frozen source
files remain byte-identical, no native state update or BV promotion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from research.spk_v5_t6abc_def_ghi.loop_v0 import LoopBoundary,digest,require
from research.spk_v5_t6jkl_mno_pqr.async_multi_v0 import scenario,make_votes,reseal
from research.spk_v5_t6jkl_mno_pqr.cumulative_gate_v0 import (
    run as replay_t6jkl,PE_SHA,BV_SHA)
from .owned_state_v0 import OwnedCState
from .stateful_multi_v0 import scenario_owned

SCHEMA='spk-v5-t6stu-vwx-yza-persistent-owned-c-state/research-v0'
ANCESTRY_SHA='4f060fa63c1d8a99bcde25d6a551f7e31f15c102d9cc7878b40317ebd0235631'
def sha_file(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def operational_probe():
    with tempfile.TemporaryDirectory(prefix='spk-state-gate-') as temp:
        path=Path(temp)/'P.sqlite'
        p=OwnedCState(path)
        first=p.choose(0,0);second=p.choose(0,0)
        fv=make_votes(first,0);sv=make_votes(second,0)
        require(p.submit(fv[0],5)=='RECEIVED','FIRST_VOTE_NOT_ACCEPTED')
        p.reopen()  # kill/reopen equivalent for honest Python process restart
        require(p.submit(fv[1],6)=='UPDATED','ATOMIC_QUORUM_COMMIT')
        before=p.audit()
        p.reopen()
        try:p.submit(fv[1],6);raise AssertionError('REPLAY_ACCEPTED')
        except LoopBoundary as exc:require(str(exc)=='NO_PENDING_OR_REPLAY','BAD_REPLAY_REJECTION')
        try:p.submit(sv[0],5);raise AssertionError('STALE_ACCEPTED')
        except LoopBoundary as exc:require(str(exc)=='OBSOLETE_POLICY_VERSION','BAD_VERSION_REJECTION')
        require(p.audit()==before and p.table=={0:11,1:11},'RECOVERY_OR_CAS_DRIFT')
        p.close()
        # A real privileged host can impersonate D, and this database is not a
        # TEE, enclave, signed hardware boundary or authenticated provenance.
        bad=OwnedCState(Path(temp)/'host.sqlite')
        d=bad.choose(0,0);v=make_votes(d,0)
        bad.submit(v[0],5)
        fake=reseal({**v[0]['vote'],'receiver':'D'})
        require(bad.submit(fake,6)=='UPDATED','HOST_IMPERSONATION_COUNTEREXAMPLE_MISSING')
        require(bad.audit()['updates']==1,'FORGED_COMMIT_NOT_RECORDED')
        bad.close()
        # Mutate materialized state with privileged DB connection. Detection is
        # fail closed without a valid history; the host can reseal whole history.
        altered=OwnedCState(Path(temp)/'tamper.sqlite')
        altered.db.execute('UPDATE policy SET choice=11 WHERE cue=0')
        try:altered.audit();raise AssertionError('CORRUPTION_ACCEPTED')
        except LoopBoundary as exc:require(str(exc)=='MATERIALIZED_POLICY_DRIFT','WRONG_CORRUPTION_FAILURE')
        altered.close()
        return {'pending_versions_not_reused':True,'durable_vote_and_commit_recovered':True,
                'one_commit_after_reopen':True,'duplicate_rejected_after_reopen':True,
                'stale_pending_vote_rejected':True,'privileged_host_impersonation_succeeds':True,
                'privileged_DB_mutation_detected_without_reseal':True,
                'reference_transaction_ledger_sha256':before['ledger_tip'],
                'reference_transaction_state_sha256':before['state_digest']}

def run(root='.',strict=True):
    root=Path(root)
    prior=root/'research/spk_v5_t6stu_vwx_yza/reference/t6jkl-mno-pqr-cumulative.json'
    require(prior.is_file() and not prior.is_symlink() and sha_file(prior)==ANCESTRY_SHA,'ANCESTRAL_REPORT_PIN_DRIFT')
    old=json.loads(prior.read_bytes())
    require(old['status']=='MULTI_RECEIVER_ASYNC_MODEL_PLASTICITY_ONLY' and
        old['T6JKL']['trained_joint_successes']==80 and old['T6JKL']['control_joint_successes']==48 and
        old['native_learning'] is False and old['promotion_allowed'] is False,'ANCESTRAL_REPORT_CONTRACT')
    pe=root/'spk_architecture_v1/pe_execution_v1b.py';bv=root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
    require(sha_file(pe)==PE_SHA and sha_file(bv)==BV_SHA,'FROZEN_SOURCE_DRIFT')
    before=(sha_file(pe),sha_file(bv))
    if strict:
        previous=replay_t6jkl(root,True)
        blob=(json.dumps(previous,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
        require(hashlib.sha256(blob).hexdigest()==ANCESTRY_SHA,'ANCESTRAL_REPLAY_DRIFT')
    settings=[{}, {'learn':False},{'mode':'reverse'},{'mode':'jitter','seed':42},
              {'mode':'jitter','seed':42,'drop_mod':7},{'conflict_contexts':(0,)},
              {'drop_mod':1},{'budget':1}]
    parity=[]
    for params in settings:
        inherited=scenario(**params)
        owned=scenario_owned(**params)
        rebooted=scenario_owned(**params,reopen_each_batch=True)
        require(all(owned[k]==v and rebooted[k]==v for k,v in inherited.items()),
                'OWNED_STATE_SCENARIO_PARITY')
        require(owned==rebooted,'REBOOT_DRIFT')
        parity.append({'scenario':params or {'default':True},'episodes':owned['episodes'],
            'joint_successes':owned['joint_successes'],'updates':owned['updates'],
            'ledger_events':owned['audit']['ledger_events'],
            'ledger_tip':owned['audit']['ledger_tip'],
            'rows_sha256':owned['rows_sha256'],
            'transcripts_sha256':owned['transcripts_sha256']})
    require([x['joint_successes'] for x in parity]==[80,48,80,80,80,40,48,44],
            'INHERITED_SCORES_DRIFT')
    require([x['updates'] for x in parity]==[8,0,8,8,8,4,0,2],
            'INHERITED_ADAPTATION_DRIFT')
    extra=[scenario_owned(mode='jitter',seed=i,reopen_each_batch=True) for i in range(10)]
    require(all(x['joint_successes']==80 and x['updates']==8 for x in extra),'TEN_SEED_PARITY')
    probe=operational_probe()
    require((sha_file(pe),sha_file(bv))==before,'FROZEN_MUTATION')
    return {'schema':SCHEMA,'status':'PERSISTENT_OWNED_C_RESEARCH_PE_FRAGMENT_ONLY',
        'T6STU':{'owner':'C','PE_ID':'PE-C-RESEARCH','domain':'P','mode':'execute',
            'implementation':'SQLite WAL FULL synchronous host-managed research adapter',
            'atomic_issue_vote_quorum_commit':True,'state_update_writes_versioned_P':True,
            'native_SPK_memory_contract_bound':False,
            'original_PE_compute_used':True,'frozen_BV_scheduler_used':False},
        'T6VWX':{'scenarios':len(parity),'scenarios_reopened_each_batch':len(parity),
            'recovered_parity_byte_exact':True,'case_results':parity,
            'ten_restarted_jitter_seeds_successes':[x['joint_successes'] for x in extra],
            'model_control_successes':48,'model_adaptive_successes':80,
            'model_adaptive_updates':8,'source_T6_jkl_replay_byte_exact':bool(strict)},
        'T6YZA':probe,
        'reference_T6_JKL_MNO_PQR_SHA256':ANCESTRY_SHA,
        'frozen_PE_sha256':PE_SHA,'frozen_BV_sha256':BV_SHA,
        'original_source_pins':12 if strict else 0,
        'host_can_forge':True,'host_can_replace_full_SQLite_ledger':True,
        'A_sensor_authenticated':False,'D_sensor_authenticated':False,'C_source_authenticated':False,
        'native_C_policy_modified':False,'native_BV_credit':0,'native_learning':False,
        'promotion_allowed':False,
        'limits':[
            'P owner C is an explicit host-managed research-state model, not adoption by frozen SPK Memory Contract or native PE scheduler',
            'Atomic SQLite WAL recovery protects against ordinary interrupted transactions and duplicate delivery, not a privileged host rewrite',
            'Eight prior synthetic scenario results are replayed byte-exact but all goals, PE fragment graph and receiver evidence are host authored',
            'No sensor attestation, no native semantic Back Validation, no native learning, no physical causal inference',
            'Crash recovery is tested as process/connection interruption and restart; power-loss durability depends on host filesystem and SQLite guarantees']}

def main():
    cli=argparse.ArgumentParser();cli.add_argument('--root',default='.');cli.add_argument('--out',required=True)
    args=cli.parse_args();target=Path(args.out)
    require(not target.exists() and not target.is_symlink(),'REPORT_EXISTS')
    result=run(args.root,True)
    target.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8')

if __name__=='__main__':main()
