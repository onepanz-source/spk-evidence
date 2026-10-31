"""T9VWX: explicit proposed native P-memory target and DENY boundary.

Reference-v1 grant may be inspected and mapped but NEVER promoted to an
SPK frozen Memory Contract authorization; no native provider is present.
"""
from __future__ import annotations
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import ensure,digest

SCHEMA='spk-v1-reference-P-target-mapping/research-v1'
class NativeUnavailable(Exception):pass

def target_for(*,owner='C',domain='P',mode='execute',cue,pe='PE-C-RESEARCH',version):
    ensure(owner=='C','TARGET_OWNER_DENIED')
    ensure(domain=='P','TARGET_DOMAIN_DENIED')
    ensure(mode=='execute','TARGET_MODE_DENIED')
    ensure(pe=='PE-C-RESEARCH','TARGET_PE_DENIED')
    ensure(type(cue) is int and cue in (0,1),'TARGET_CONTEXT_DENIED')
    ensure(type(version) is int and version>=0,'TARGET_VERSION_DENIED')
    return {'schema':SCHEMA,'owner':'C','domain':'P','mode':'execute',
            'pe_id':pe,'context':cue,'expected_version':version,
            'target_id':f'P/C/context-{cue}', 'grant_scope':'single-version-CAS',
            'authority':'REFERENCE_V1_ONLY','native_memory_grant':False}

def project_grant(engine, grant_id):
    ensure(type(grant_id) is int and grant_id>=0,'GRANT_ID_DOMAIN')
    g=engine.db.execute('SELECT * FROM p_grant WHERE id=?',(grant_id,)).fetchone()
    ensure(g is not None and g['consumed']==1,'GRANT_UNAVAILABLE')
    ep=engine.db.execute('SELECT * FROM episode WHERE id=?',(g['episode_id'],)).fetchone()
    ensure(ep is not None and ep['reference_grant']==grant_id,'GRANT_NOT_SETTLED')
    target=target_for(cue=g['cue'],version=g['expected_version'])
    return {'target':target,'receipt_sha256':g['verdict_digest'],
            'source_event_custody':'REFERENCE_V1_VERIFIED',
            'reference_grant_id':grant_id,'mapped_reference_grant':True,
            'native_grant_id':None,'native_admission':'DENIED_NO_NATIVE_MEMORY_CONTRACT_PORT'}

def native_authorize(*_args, **_kwargs):
    raise NativeUnavailable('NATIVE_MEMORY_CONTRACT_PORT_NOT_IMPLEMENTED')
