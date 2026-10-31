"""Read-only inventory of actual SPK Memory Contract source surfaces.

This module NEVER imports/executes discovered code and NEVER grants memory.
The source survey is a *discovery*, not authorization, signature, or API adoption.
"""
from __future__ import annotations
import ast,hashlib
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import ensure,Reject,digest

ROOTS=('spk_architecture_v1','spk_memory','spk_compiler','spk_simulator')
KEYWORDS=('memory','contract','authorization','admission','access','resource','transaction','ownership')
PINNED_RUNTIME=('spk_architecture_v1/pe_execution_v1b.py','spk_backvalidation_v0/live_dual_scheduler_v0e.py')
MAX_BYTES=256000

def sha(b):return hashlib.sha256(b).hexdigest()

def inspect_file(root,rel):
    root=Path(root).resolve(strict=True);path=root/rel
    ensure(path.is_file() and not path.is_symlink(),'SOURCE_NOT_REGULAR')
    ensure(path.resolve().is_relative_to(root),'SOURCE_OUTSIDE_ROOT')
    ensure(path.stat().st_size <= MAX_BYTES,'SOURCE_TOO_LARGE')
    raw=path.read_bytes();tree=ast.parse(raw,filename=str(rel))
    exports=[]
    for n in tree.body:
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
            exports.append({'kind':'function','name':n.name,'args':[a.arg for a in n.args.args]})
        elif isinstance(n,ast.ClassDef):
            methods=sorted(m.name for m in n.body if isinstance(m,(ast.FunctionDef,ast.AsyncFunctionDef)) and not m.name.startswith('__'))
            exports.append({'kind':'class','name':n.name,'methods':methods})
    return {'path':rel.as_posix(),'sha256':sha(raw),'bytes':len(raw),'surface':exports}

def probe(root):
    root=Path(root).resolve(strict=True);sources=[]
    for prefix in ROOTS:
        folder=root/prefix
        if not folder.is_dir() or folder.is_symlink():continue
        for path in sorted(folder.glob('*.py')):
            if not any(w in path.stem.lower() for w in KEYWORDS):continue
            sources.append(inspect_file(root,path.relative_to(root)))
    ensure(len(sources)<=80,'UNBOUNDED_SURVEY')
    return {'candidate_count':len(sources),'candidates':sources,
            'candidate_digest':digest(sources),
            'source_contract_api_authorized':False,
            'native_memory_grant_executed':False,
            'reason':'READ_ONLY_SURVEY_HAS_NO_AUTHORIZED_NATIVE_ENTRYPOINT'}

def read_only_contract_request(*,owner,domain,mode,pe_id,context,version):
    """Strict, typed request mapping. A proposal, never an authorized native call."""
    ensure(type(owner) is str and owner=='C','OWNER_SCOPE')
    ensure(type(domain) is str and domain=='P','DOMAIN_SCOPE')
    ensure(type(mode) is str and mode=='execute','MODE_SCOPE')
    ensure(type(pe_id) is str and pe_id=='PE-C-RESEARCH','PE_SCOPE')
    ensure(type(context) is int and context in (0,1),'CONTEXT_SCOPE')
    ensure(type(version) is int and version>=0,'VERSION_SCOPE')
    r={'owner':owner,'domain':domain,'mode':mode,'pe_id':pe_id,
       'context':context,'expected_version':version}
    return {'request':r,'request_digest':digest(r),'native_admission':'DENIED_NO_AUTHORIZED_MEMORY_CONTRACT_CALL',
            'native_grant':False,'native_write':False}

def reject_native_promotion(reference_receipt,claimed_native_receipt=None):
    """Explicitly forbid rebranding research P grants as native Memory grants."""
    ensure(isinstance(reference_receipt,dict),'REFERENCE_RECEIPT_INVALID')
    for key in ('owner','domain','mode','pe_id','context','expected_version'):
        ensure(key in reference_receipt,'REFERENCE_SCOPE_INCOMPLETE')
    request=read_only_contract_request(owner=reference_receipt['owner'],domain=reference_receipt['domain'],
        mode=reference_receipt['mode'],pe_id=reference_receipt['pe_id'],context=reference_receipt['context'],
        version=reference_receipt['expected_version'])
    # A host-supplied native-looking claim cannot establish native origin.
    return {'reference_request_digest':request['request_digest'],
            'claimed_native_receipt_present':claimed_native_receipt is not None,
            'promotion_allowed':False,'native_grants':0,'native_writes':0,
            'reason':'UNTRUSTED_HOST_ASSERTION_CANNOT_BECOME_NATIVE_MEMORY_AUTHORITY'}
