"""T7MNO bounded C/P write intent at an experimental host-owned boundary.

Not SPK Memory Contract authorization. Native P writes remain unavailable.
"""
from __future__ import annotations
from research.spk_v5_t6abc_def_ghi.loop_v0 import digest
from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import check,verify_source
from .semantic_custody_v0 import verify as verify_custody

SCHEMA='spk-v5-t7mno-shadow-P-write-intent/v0'

def prepare(source,issued,received,*,drop_forward=False):
    checked=verify_custody(source,issued,received,drop_forward=drop_forward)
    outcome=checked['outcome']; receipt=checked['C_receipt']
    return {'schema':SCHEMA,'owner':'C','pe_id':'PE-C-RESEARCH','domain':'P',
        'mode':'execute','native_authorized':False,'scope':'research-only',
        'operation':'BOUNDED_POLICY_SWITCH_IF_WRONG',
        'decision_id':issued['id'],'cue':issued['cue'],'expected_version':issued['version'],
        'expected_choice':issued['choice'],'outcome':outcome,
        'structural_BV_completed':receipt is not None,
        'receipt_sha256':digest(receipt) if receipt is not None else None,
        'source_sha256':checked['source_sha256'],'update_candidate':outcome=='WORSENED'}

def settle(store,source,issued,received,intent,*,drop_forward=False):
    expected=prepare(source,issued,received,drop_forward=drop_forward)
    check(type(intent) is dict and intent==expected,'P_INTENT_DRIFT')
    check(intent['owner']=='C' and intent['domain']=='P' and intent['mode']=='execute'
          and intent['native_authorized'] is False,'NATIVE_AUTHORITY_FORGERY')
    # Native state is NEVER modified. This uses the prior host-owned SQLite adapter.
    evidence=verify_source(source,issued['choice'],issued['goal'],drop_forward=drop_forward)
    committed=store.settle(issued,evidence)
    check(committed['updated'] is False or intent['update_candidate'],'UNAUTHORIZED_UPDATE')
    return committed
