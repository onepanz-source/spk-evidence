#!/usr/bin/env python3
"""T4TUV: counterexample to host-commissioned C authority, research ONLY.

T: With *no* scheduler/source execution, reproduce T4QRS A receipts from pinned
   earlier source-output evidence and host-generated commitments.
U: Explicitly reject an assertion of native neuronal provenance when the
   execution-owned C emitter/verifier does not exist.
V: Fail-closed custody, AST integration seam, 2 independent subprocess runs.

No frozen source modifications, no new training, no trusted sensor.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter
from contextlib import redirect_stdout
from hashlib import sha256
import io
import json
from pathlib import Path
import secrets
from research.spk_v5_t4qrs import t4qrs as q

SCHEMA='spk-v5-t4tuv-host-authority-counterexample/research-v0'
STATUS='HOST_CACHED_EVIDENCE_REPRODUCES_A_LEDGER_NO_C_ORIGIN'
QRS_REPORT_SHA='174176faf2dec41a0120008bbc3e5813cf89291aec6de6cf953079941d2f54b4'
GHI_REPORT_SHA='dc98a1a5e45270d665e5119540ae960e405f4d02b703bd0c52d04202873abef3'
NO_SOURCE='C_EMITTER_EXECUTION_PROVENANCE_NOT_AVAILABLE'
GUARD=q.ELIGIBLE
class GateError(q.GateError):pass

def need(cond,code):
    if not cond:raise GateError(code)

def require_file(path,sha,reason):
    p=Path(path)
    need(p.is_file() and not p.is_symlink(),reason+'_MISSING_OR_SYMLINK')
    need(q.sha(p)==sha,reason+'_SHA_DRIFT')
    return q.read(p)

def references(root):
    root=Path(root)
    ref=q.load_reference(root/'research/spk_v5_t4qrs/reference/t4nop-receiver-boundary.json')
    ghi=require_file(root/'research/spk_v5_t4jkl/reference/t4ghi-one-pass-sign.json',GHI_REPORT_SHA,'GHI_REPORT')
    old=require_file(root/'research/spk_v5_t4tuv/reference/t4qrs-process-receiver-port.json',QRS_REPORT_SHA,'QRS_ORIGINAL')
    need(ghi.get('status')=='SINGLE_SOURCE_SIGN_VISIBILITY_RESEARCH_ONLY' and
         len(ghi.get('H_rows',[]))==180,'GHI_SHAPE_INVALID')
    need(old.get('schema')==q.SCHEMA and old.get('status')==q.STATUS,'QRS_SCHEMA_INVALID')
    need(old.get('producer',{}).get('original_BV_calls')==180 and old.get('producer',{}).get('guard_selected')==24 and
         old.get('receiver',{}).get('committed_count')==24 and old.get('receiver',{}).get('rejected_adversarial_count')==13,
         'QRS_REFERENCE_INCONSISTENT')
    need(old.get('C_neuron_origin_authenticated') is False and old.get('native_learning_proven') is False and
         old.get('promotion_allowed') is False,'QRS_UNSAFE_PROMOTION')
    need(old.get('source_pins')==ref['N_source_pins'],'QRS_SOURCE_PINS_DIFFER')
    return ref,ghi,old

def source_seam(root):
    """Static location of the frozen-call seam and subsequent adapter."""
    files={
      'research/spk_v5_t4ghi/t4ghi.py':('source_once',['execute_live_v0e']),
      'research/spk_v5_t4qrs/t4qrs.py':('producer',['source_once','observe_forward_result','events_packet','precommit'])}
    out={}
    for relative,(function,expected) in files.items():
        path=Path(root)/relative
        need(path.is_file() and not path.is_symlink(),'SEAM_SOURCE_MISSING:'+relative)
        tree=ast.parse(path.read_text(encoding='utf-8'))
        body=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==function]
        need(len(body)==1,'SEAM_FUNCTION_AMBIGUOUS:'+function)
        calls=[n for n in ast.walk(body[0]) if isinstance(n,ast.Call)]
        found={label:sorted({n.lineno for n in calls if (isinstance(n.func,ast.Name) and n.func.id==label) or
                  (isinstance(n.func,ast.Attribute) and n.func.attr==label)}) for label in expected}
        need(all(found.values()),'SEAM_CALLSITE_ABSENT:'+function)
        out[relative]={'function':function,'call_sites':found,'source_sha256':q.sha(path)}
    return out

def cached_producer(root,work):
    """NO BV call, no T3h, no source_once; use archival JSON exclusively.

    Outputs deliberately have exactly T4QRS's host-commissioned schema and
    producer-summary, to demonstrate that QRS's A-ledger cannot distinguish.
    """
    ref,ghi,old=references(root)
    commitments={};out=[];counts=Counter()
    for i,(row,cached) in enumerate(zip(ref['O_rows'],ghi['H_rows'])):
        need(cached.get('source_sha256')==row['source_sha256'],'CACHED_SHA_DIFFER_'+str(i))
        need(cached.get('C_sign_candidate_from_same_source_forward_output')==row['observed_sign'],
             'CACHED_SIGN_DIFFER_'+str(i))
        counts[row['research_classification']]+=1
        if row['research_classification']!=GUARD:continue
        need(cached.get('C_B_A_emission_candidate_consistent') is True,'ARCHIVED_TRIPLE_MISSING_'+str(i))
        pkt=q.events_packet(i,row['source_sha256'],cached)
        q.validate_packet_structure(pkt,row)
        token=secrets.token_hex(32)
        commitments[str(i)]=q.precommit(pkt,token)
        out.append({'payload':pkt,'token':token})
    need(len(out)==24 and counts==Counter(ref['O_classification_counts']),'ARCHIVED_SELECTION_DRIFT')
    enrollment={'schema':q.ENROLL_SCHEMA,'boundary':'HOST_TRUSTED_BOOTSTRAP_NOT_NATIVE_C_AUTHORITY',
                'commitments':commitments,'reference_sha256':q.REF_SHA}
    q.write(work/'enrollment.json',enrollment)
    q.write(work/'producer-outbox.json',{'messages':out,'schema':'spk-v5-t4qrs-C-adapter-outbox/research-v0'})
    # This intentionally mimics an ORIGINAL-CALLS=180 producer summary even
    # though this checkpoint invoked the scheduler exactly zero times.
    q.write(work/'producer-summary.json',{'original_BV_calls':180,'guard_selected':len(out),
        'classification_counts':dict(sorted(counts.items())),
        'semantic_signs':dict(sorted(Counter(str(x['payload']['semantic_sign']) for x in out).items())),
        'source_pin_count':len(ref['N_source_pins']),'adapter_is_not_native_C':True})
    q.write(work/'actual-execution-custody.json',{'actual_BV_source_calls_in_this_run':0,
        'source_origin':'ARCHIVED_HOST_CONTROLLED_JSON_ONLY',
        'producer_summary_original_calls_claim':180,
        'claim_refuted_by_constructed_counterexample':True,
        'native_C_authored_packets':0})

def native_semantic_claim(candidate):
    """A payload cannot establish native authority without runtime verifier.

    This deliberately has no affirmative branch; a future runtime-owned verifier
    requires a new, reviewed interface and tests, not a new JSON field.
    """
    need(isinstance(candidate,dict),'NATIVE_CANDIDATE_INVALID')
    raise GateError(NO_SOURCE)

def audit(root,work,output):
    from research.spk_v5_t4nop import t4nop
    ref,ghi,old=references(root)
    actual=q.read(work/'actual-execution-custody.json')
    need(actual=={'actual_BV_source_calls_in_this_run':0,
        'source_origin':'ARCHIVED_HOST_CONTROLLED_JSON_ONLY',
        'producer_summary_original_calls_claim':180,
        'claim_refuted_by_constructed_counterexample':True,
        'native_C_authored_packets':0},'EXPERIMENT_EXECUTION_CUSTODY_INVALID')
    # Reuse *unaltered* historical AReceiver + B relay + T4QRS audit.
    with redirect_stdout(io.StringIO()):
        q.audit(root,root/'research/spk_v5_t4qrs/reference/t4nop-receiver-boundary.json',work,
                work/'counterfeit-qrs-report.json')
    oldsha=q.sha(work/'counterfeit-qrs-report.json')
    need(oldsha==QRS_REPORT_SHA,'COUNTERFACTUAL_REPORT_PARITY_FAILED')
    own=q.read(work/'A-owned-ledger.json')
    need(own.get('accepted')==24 and own.get('native_semantic_credit')==0 and own.get('trusted_bootstrap_owned_by_host') is True,
         'COUNTERFACTUAL_A_LEDGER_INVALID')
    need(q.digest(own['entries'])==old['receiver']['ledger_sha256'],'COUNTERFACTUAL_A_LEDGER_SHA_MISMATCH')
    pins=t4nop.custody(root,t4nop.load_reference(root/'research/spk_v5_t4nop/reference/t4jklm-control-flag.json'))
    need(pins==ref['N_source_pins'],'SOURCE_PINS_CHANGED')
    refusal={}
    for name,data in [('empty',{}),('fake_native_flag',{'native_C_authored':True}),
                      ('fake_signature',{'semantic_sign':1,'source_identity':'C','authenticator':'sha256'}),
                      ('fake_envelope',{'semantic_sign':-1,'source_identity':'C','C_emission_id':'em123',
                                        'causal_parent_id':'parent','authenticator':'signed'})]:
        try:native_semantic_claim(data)
        except GateError as e:refusal[name]=str(e)
        else:raise GateError('FORGED_NATIVE_CLAIM_ACCEPTED:'+name)
    need(set(refusal)=={'empty','fake_native_flag','fake_signature','fake_envelope'} and
         set(refusal.values())=={NO_SOURCE},'NATIVE_CLAIM_REFUSAL_INVALID')
    seam=source_seam(root)
    need(len(pins)==12,'SOURCE_PIN_COUNT_INVALID')
    report={'schema':SCHEMA,'status':STATUS,
        'T_cached_source_invocations_this_run':0,
        'T_QRS_report_reproduced_from_cached_data':True,
        'T_reconstructed_QRS_sha256':oldsha,
        'T_original_QRS_sha256':QRS_REPORT_SHA,
        'T_same_A_ledger_sha256':old['receiver']['ledger_sha256'],
        'T_A_process_accepted_cached_packets':24,
        'T_A_process_adversarial_rejections':13,
        'T_counterexample':'An actor with the existing host enrollment authority can satisfy the QRS receiver and audit from previously saved JSON, without running C or BV this time',
        'U_native_source_authentication_available':False,
        'U_natively_verified_semantic_receipts':0,
        'U_native_claim_rejections':refusal,
        'U_native_origin_required_fields':ref['O_missing_semantic_contract_fields'],
        'U_missing_runtime_owned_issuer':'No execution-owned C origin/verification primitive is present in the observed contract',
        'V_integration_seam':seam,
        'source_pins':pins,'reference_T4NOP_sha256':q.REF_SHA,
        'reference_T4GHI_sha256':GHI_REPORT_SHA,
        'reference_T4QRS_sha256':QRS_REPORT_SHA,
        'native_receiver_semantic_receipt_proven':False,
        'native_learning_proven':False,'promotion_allowed':False,
        'limits':['This is a constructive host-origin counterexample, not a new native BV experiment',
                  'Zero original BV executions in this checkpoint; the reconstructed QRS report repeats a claim of 180 from forged producer-summary metadata',
                  'SHA-pinned archive rows are evidence of prior computation, not a fresh neuronal emission or C-owned proof',
                  'T4QRS A ledger is secure only relative to a trusted host enrollment, not independent C-origin authority',
                  'Native integration requires a runtime-owned C emission and a verified receiver custody path; none is claimed here',
                  'No independent sensor authority, independent goal truth or learning update']}
    q.write(output,report)
    print('T4TUV',STATUS,'cached issuer calls 0','A receiver accepts 24','counterfeit QRS exact SHA',oldsha)
    print('SHA256',q.sha(output))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('stage',choices=('cached','relay','receiver','audit'))
    p.add_argument('--root',type=Path,default=Path('.'))
    p.add_argument('--work',type=Path,required=True)
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    try:
        root=a.root.resolve()
        if a.stage=='cached':cached_producer(root,a.work)
        elif a.stage=='relay':q.relay(a.work)
        elif a.stage=='receiver':q.receiver(root/'research/spk_v5_t4qrs/reference/t4nop-receiver-boundary.json',a.work)
        else:
            need(a.out is not None,'REPORT_OUTPUT_REQUIRED')
            audit(root,a.work,a.out)
    except (GateError,ValueError,TypeError,KeyError,AssertionError,FileNotFoundError,OSError) as e:
        raise SystemExit('T4TUV FAIL CLOSED: '+str(e))
if __name__=='__main__':main()
