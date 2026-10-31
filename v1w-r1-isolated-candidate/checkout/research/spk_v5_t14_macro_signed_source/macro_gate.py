"""T14 cumulative security boundary: signed laboratory semantic receipts only.

WARNING: generated laboratory private key is held by this experiment harness,
not a physically independent A observer. A signature authenticates a key,
not the actual goal, measurement, or causal validity of the A verdict.
Original A1d accesses are executed only in strict fwork mode.
"""
from __future__ import annotations
import argparse,hashlib,json,sqlite3,subprocess,tempfile
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import ensure,digest
from research.spk_v5_t9abc_def_ghi.cumulative_concurrency_gate import tasks
from research.spk_v5_t12_macro_native_memory_seam.native_bridge_v1d import sha,pinned_source_catalog
from research.spk_v5_t13_macro_original_access_guard.access_guard_v1 import ORIGINAL_A1D_SHA
from .signed_boundary_v1 import SignedSourceGatedV1,sign_detached_for_lab

PARENT_SHA='54686e49ec2e66daf317d3e4ed1be3f1dc7ac7a070773319632cd265e4e59b31'
SCHEMA='spk-v5-t14-macro-detached-feedback-and-credit-custody/research-v0'


def laboratory_keys(td:Path):
    priv=td/'lab-private-OUTSIDE_RUNTIME.pem';pub=td/'lab-public.pem'
    subprocess.run(['openssl','genpkey','-algorithm','ED25519','-out',str(priv)],
                   check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    subprocess.run(['openssl','pkey','-in',str(priv),'-pubout','-out',str(pub)],
                   check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    return priv,pub.read_bytes()


def scenario(root,*,strict:bool,crash_each_wave=False):
    with tempfile.TemporaryDirectory(prefix='spk-t14-attestation-') as tmp:
        path=Path(tmp);priv,pub=laboratory_keys(path)
        stub=(None if strict else lambda c,g:{'kind':'TEST_ONLY','choice':c,'goal':g,
                                                'original_learning_P_grants':0})
        e=SignedSourceGatedV1(path/'engine.sqlite',public_key_pem=pub,root=root,
                              test_only=not strict,test_witness=stub)
        queue=list(enumerate(tasks()));byidx={};waves=0;slots=0;attested=0
        try:
            while queue:
                selected=[];contexts=set()
                for i,(cue,goal) in queue:
                    if len(selected)>=3:break
                    if cue in contexts:continue
                    selected.append((i,cue,goal));contexts.add(cue)
                ensure(selected,'T14_ADMISSION_DEADLOCK')
                for i,cue,goal in selected:byidx[i]=e.submit(cue,goal)
                waves+=1
                while True:
                    res=e.step()
                    if res is None:break
                    slots+=1
                    if res['kind']=='PE_A':
                        episode=res['episode'];msg=e.expected_message(episode)
                        if json.loads(msg)['verdict']=='WORSENED':
                            signature=sign_detached_for_lab(priv,msg)
                            e.ingest(episode,msg,signature);attested+=1
                if crash_each_wave:e.reopen()
                queue=[q for q in queue if q[0] not in byidx]
            rows=[e.result(byidx[i]) for i in range(len(byidx))]
            audit=e.audit();orig=e.audit_original_access();mem=e.audit_owned_memory();att=e.audit_signed_source()
            row_hash=digest([{'cue':r['cue'],'goal':r['goal'],'choice':r['choice'],
                         'version':r['version'],'outcome':r['outcome'],'grant':r['grant']} for r in rows])
            out={'episodes':len(rows),'waves':waves,'dispatcher_slots':slots,
                 'successes':sum(r['choice']==r['goal'] for r in rows),
                 'row_digest':row_hash,'grants':audit['reference_v1_tick_grants'],
                 'P_commits':mem['new_v1_memory_P_commits'],
                 'external_test_signed_negative_receipts':attested,
                 'attestation_grants':att['signed_P_grants'],
                 'original_execution_access_witnesses':orig['original_access_witnesses'],
                 'test_only_memory_witnesses':orig['test_only_witnesses'],
                 'original_A1d_executions_for_witnesses':orig['original_A1d_executions_for_witnesses'],
                 'original_P_learning_grants':0,'authentic_external_A_sensor':False,
                 'external_signer_privately_controlled':False,
                 'generated_laboratory_signer':True,
                 'laboratory_private_key_exported_in_archive':False,
                 'receipt_schema':SCHEMA,'host_controls_task_and_goal':True}
            ensure(out['grants']==out['P_commits']==out['attestation_grants'], 'T14_CUSTODY_CARDINALITY_DRIFT')
            ensure(out['grants']==8,'T14_SIGNED_CREDIT_DRIFT')
            return out
        finally:e.close()


def missing_receipt_counterexample(root,*,strict:bool):
    """A genuine negative C receipt must roll back when external proof is absent.

    Reopen with the pending event, provide a separately signed lab observation,
    and prove one (not two) CAS commits on recovery. No implicit auto-signing.
    """
    with tempfile.TemporaryDirectory(prefix='spk-t14-negative-') as td:
        td=Path(td);private,pub=laboratory_keys(td)
        stub=(None if strict else lambda c,g:{'kind':'TEST_ONLY','choice':c,'goal':g,
                                             'original_learning_P_grants':0})
        e=SignedSourceGatedV1(td/'negative.sqlite',public_key_pem=pub,root=root,
                            test_only=not strict,test_witness=stub)
        try:
            ep=e.submit(0,11)
            a=[]
            for _ in range(4):a.append(e.step()['kind'])
            ensure(a==['PE_C','PE_B','PE_A','SEM_A_B'],'T14_NEGATIVE_PRECONDITION')
            try:e.step()
            except sqlite3.IntegrityError as exc:
                ensure('P_REFERENCE_PROVIDER_DENIED' in str(exc),'T14_UNEXPECTED_ROLLBACK')
            else:raise ValueError('T14_UNSIGNED_GRANT_ACCEPTED')
            before=e.db.execute('SELECT choice,version FROM p WHERE cue=0').fetchone()
            assert tuple(before)==(12,0)
            assert e.db.execute('SELECT COUNT(*) FROM p_grant').fetchone()[0]==0
            assert e.db.execute("SELECT COUNT(*) FROM event WHERE status='QUEUED' AND kind='SEM_B_C'").fetchone()[0]==1
            e.reopen()
            msg=e.expected_message(ep)
            e.ingest(ep,msg,sign_detached_for_lab(private,msg))
            assert e.step()['kind']=='SEM_B_C'
            assert e.step() is None
            assert e.result(ep)['grant']==0
            assert e.audit_signed_source()['signed_P_grants']==1
            e.reopen()
            assert e.audit()['reference_v1_tick_grants']==1
            return {'unsigned_negative_receipt_denied_atomically':True,
                    'pending_C_feedback_after_denial':1,
                    'P_grants_before_signature':0,
                    'P_grants_after_valid_signature':1,
                    'reopen_and_replay_single_commit':True,
                    'real_A_sensor_attested':False}
        finally:e.close()

def report(root,*,strict:bool):
    root=Path(root).resolve(strict=True)
    parent=root/'research/spk_v5_t14_macro_signed_source/reference/t13-original-access.json'
    ensure(sha(parent)==PARENT_SHA,'T14_PARENT_T13_DRIFT')
    t13=json.loads(parent.read_text())
    ensure(t13['M3_reference_v1_runtime']['original_witness']['original_access_witnesses']==8,
           'T14_PARENT_T13_ORIGINAL_WITNESSES_INCOMPLETE')
    if strict:
        ensure(sha(root/'spk_architecture_v1/pe_fault_v1d.py')==ORIGINAL_A1D_SHA,
               'T14_A1D_DRIFT')
        ensure(pinned_source_catalog(root,require_sources=True)['original_count']==5,
               'T14_ORIGINAL_MEMORY_MISSING')
    signed=scenario(root,strict=strict)
    unsigned=missing_receipt_counterexample(root,strict=strict)
    reopened=scenario(root,strict=strict,crash_each_wave=True)
    expected=t13['M3_reference_v1_runtime']
    ensure(signed['row_digest']==reopened['row_digest']==expected['row_digest'] and
           signed['successes']==reopened['successes']==88 and
           signed['grants']==reopened['grants']==8 and
           signed['waves']==reopened['waves']==48,'T14_SIGNED_LAB_T13_PARITY')
    ensure(unsigned['unsigned_negative_receipt_denied_atomically'] and
           unsigned['P_grants_before_signature']==0 and
           unsigned['P_grants_after_valid_signature']==1,'T14_UNSIGNED_FAIL_OPEN')
    ensure((signed['original_execution_access_witnesses']==8 and
            reopened['original_execution_access_witnesses']==8) if strict else
           (signed['test_only_memory_witnesses']==8 and reopened['test_only_memory_witnesses']==8),
           'T14_ORIGINAL_ACCESS_CUSTODY')
    return {'schema':SCHEMA,'source_T13_SHA256':PARENT_SHA,
            'M1_signed_source_protocol':'Ed25519 over canonical A event/PE digest + C decision/version/goal',
            'M2_unsigned_denial_and_recovery':unsigned,
            'M3_lab_signature_preserves_T13':signed,
            'M4_recovery_parity':reopened,
            'M5_original_A1d_memory_access_during_signed_C_grant':strict,
            'M6_trust_and_promotion':{
                'signature_authenticates_public_key_only':True,
                'separate_independent_A_sensor_attested':False,
                'observed_goal_authenticity_proven':False,
                'host_cannot_change_runtime':False,
                'host_remains_privileged':True,
                'lab_private_key_generated_only_during_gate':True,
                'original_SPK_P_learning_grants':0,
                'native_BV_semantic_learning':False,
                'promotion_allowed':False,
                'real_external_signer_in_release':False},
            'strict_original_execution':strict,
            'native_learning':False,'promotion_allowed':False,
            'status':'SIGNED_LAB_RECEIPT_ORIGINAL_A1D_ACCESS_BARRIER_NO_NATIVE_SOURCE_OR_P_LEARNING' if strict
                     else 'LOCAL_TEST_ONLY_SIGNED_PROTOCOL_NO_ORIGINAL_A1D'}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',default='.')
    ap.add_argument('--out',required=True);ap.add_argument('--local-test-only',action='store_true')
    a=ap.parse_args();out=Path(a.out)
    ensure(not out.exists() and not out.is_symlink(),'T14_REPORT_EXISTS')
    result=report(a.root,strict=not a.local_test_only)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n')
    print('T14 LAB-SIGNED A FEEDBACK GATES ORIGINAL A1D ACCESS AND RESEARCH P; NO NATIVE SPK LEARNING')
    print('report_sha256',sha(out))
if __name__=='__main__':main()
