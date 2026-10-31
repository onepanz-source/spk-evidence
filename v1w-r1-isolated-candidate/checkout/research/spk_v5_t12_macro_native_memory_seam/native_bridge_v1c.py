"""T12: pinned original memory execution API bridge, with explicit learning boundary.

This module runs ACTUAL original frozen memory modules on an admitted A/B/C
workload when installed on fwork, not a shadow copy. Its grants authorize
original bounded execution access only, NEVER C's learning-policy P update.
All P writes remain in the distinct new-version research runtime.
"""
from __future__ import annotations
import ast, hashlib, importlib, inspect, json
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import ensure, digest, Reject

PINNED={
 'spk_architecture_v1/memory_projection_v1a.py':'3c9d74cb712bd9b40384634f830fbc0c65144573db6c3e3ebb095b1afed94b4f',
 'spk_architecture_v1/memory_access_v1b.py':'365a97fdca40cfa45098c5d253cc03b378667bd6d1578798be7df1e2c9d6be36',
 'spk_architecture_v1/memory_service_v1c.py':'8f2edf529d480d32eb6434164662f15b4cafa9bedd0fe72df58c48e10ffe24c2',
 'spk_architecture_v1/mode_memory_v1b.py':'b02bca9f45035330cf178cae01c4887edfd0f9e21c34f8766430554af6159281',
 'spk_architecture_v1/memory_exhaustion_v1d.py':'efacd81645dbc5dcbefa500d2208d44919ab54b8b2987b13648c7a4d1ab7f53a',
}
EXPORTS={
 'spk_architecture_v1/memory_projection_v1a.py':('uniform_memory_plan_v1a','admit_memory_v1a','project_execution_memory_v1a'),
 'spk_architecture_v1/memory_access_v1b.py':('issue_authority_v1b','derive_requests_v1b','authorize_requests_v1b','authorize_projection_v1b'),
 'spk_architecture_v1/memory_service_v1c.py':('memory_service_plan_v1c','serve_projection_v1c','serve_authorized_v1c'),
 'spk_architecture_v1/mode_memory_v1b.py':('issue_mode_memory_permit_v1b','serve_mode_memory_v1b'),
 'spk_architecture_v1/memory_exhaustion_v1d.py':('preflight_memory_v1d','service_verdict_v1d'),
}

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def pinned_source_catalog(root, *, require_sources=True):
    """Inspect actual bytes, no exec; never accept same-named fake module."""
    root=Path(root).resolve(strict=True); rows=[]; missing=[]
    for rel,expected in PINNED.items():
        p=root/rel
        if not p.is_file() or p.is_symlink():
            missing.append(rel); continue
        ensure(p.resolve().is_relative_to(root),'ORIGINAL_MEMORY_PATH_ESCAPE')
        ensure(sha(p)==expected,'ORIGINAL_MEMORY_SOURCE_DRIFT:'+rel)
        t=ast.parse(p.read_bytes(),filename=rel)
        functions={n.name:tuple(a.arg for a in n.args.args) for n in t.body
                   if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        for name in EXPORTS[rel]:
            ensure(name in functions,'ORIGINAL_MEMORY_API_MISSING:'+name)
        rows.append({'path':rel,'sha256':expected,
                     'api':{name:list(functions[name]) for name in EXPORTS[rel]}})
    if require_sources:ensure(not missing,'MISSING_PINNED_ORIGINAL_MEMORY_SOURCES:'+','.join(missing))
    return {'original_count':len(rows),'missing':missing,'apis':rows,'catalog_sha256':digest(rows),
            'source_loaded_by_execution':False,'learning_P_grants':0}

def _native_service_plans(case, fabric):
    """Original-only service constructors, starting with frozen BV-v0e 3/4.

    T12 v0 incorrectly guessed service capacities 16/32. Some original V1c
    APIs require PEServiceAdmissionV1c rather than CausalServicePlanV1b.
    This discovery never constructs fake plans or claims a P learning grant.
    """
    errors=[]; plans=[]
    module_names=('spk_architecture_v1.temporal_service_v1b',
                  'spk_architecture_v1.pe_service_v1c',
                  'spk_architecture_v1.pe_service_v1a',
                  'spk_architecture_v1.temporal_service_v1c')
    for module_name in module_names:
        try:module=importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name==module_name:errors.append(module_name+':MODULE_MISSING');continue
            raise
        for name in sorted(vars(module)):
            if not (name.startswith('uniform_') and 'service_plan' in name):continue
            fn=getattr(module,name)
            if not inspect.isfunction(fn) or fn.__module__!=module_name:continue
            sig=inspect.signature(fn)
            for pe,slots in ((3,4),(1,4),(4,8),(16,32)):
                kwargs={};unsupported=[]
                for key,param in sig.parameters.items():
                    if key=='fabric':continue
                    if key in ('pe_slots','slots_per_pe','service_slots_per_pe'):kwargs[key]=pe
                    elif key in ('fabric_slots_per_tick','fabric_slots','pe_slots_per_tick'):kwargs[key]=slots
                    elif key in ('max_service_span_ticks','max_ticks'):kwargs[key]=256
                    elif param.default is inspect.Parameter.empty:unsupported.append(key)
                label=f'{module_name}.{name}[{pe}/{slots}]'
                if unsupported:
                    errors.append(label+':UNKNOWN_REQUIRED:'+','.join(unsupported));break
                try:plans.append((label,fn(fabric,**kwargs)))
                except (ValueError,TypeError,KeyError,AttributeError) as exc:
                    errors.append(label+':'+type(exc).__name__+':'+str(exc)[:120])
    # Service plans are not interchangeable with original service admissions.
    # Ask the original code to issue a V1c admission where such an issuer exists.
    candidates=list(plans)
    for module_name in ('spk_architecture_v1.pe_service_v1c',
                        'spk_architecture_v1.temporal_service_v1c'):
        try:module=importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name==module_name:continue
            raise
        for name in sorted(vars(module)):
            if not (name.startswith(('admit_','issue_')) and 'service' in name):continue
            fn=getattr(module,name)
            if not inspect.isfunction(fn) or fn.__module__!=module_name:continue
            sig=inspect.signature(fn)
            for source_label,service_plan in plans:
                available={'case':case,'fabric':fabric,'plan':service_plan,
                           'service_plan':service_plan,'pe_service_plan':service_plan}
                kwargs={};unknown=[]
                for key,param in sig.parameters.items():
                    if key in available:kwargs[key]=available[key]
                    elif param.default is inspect.Parameter.empty:unknown.append(key)
                label=module_name+'.'+name+'('+source_label+')'
                if unknown:
                    errors.append(label+':UNKNOWN_REQUIRED:'+','.join(unknown));continue
                try:candidates.append((label,fn(**kwargs)))
                except (ValueError,TypeError,KeyError,AttributeError) as exc:
                    errors.append(label+':'+type(exc).__name__+':'+str(exc)[:140])
    if not candidates:raise ValueError('NO_ORIGINAL_SERVICE_CANDIDATES:'+repr(errors))
    return candidates,errors

def original_native_execution_probe(root):
    """Run original admissible memory projection and original access authority.

    Return a *diagnostic* if the original bounded memory API has different
    requirements. An exception is never recast into a successful grant.
    """
    catalog=pinned_source_catalog(root)
    from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import case_for
    from spk_architecture_v1.pe_fabric_v1a import plan_v1a
    from spk_architecture_v1.pe_execution_v1b import execute_on_pes_v1b
    from spk_architecture_v1.memory_projection_v1a import (uniform_memory_plan_v1a,
                           admit_memory_v1a, project_execution_memory_v1a)
    from spk_architecture_v1.memory_access_v1b import (issue_authority_v1b,
                           authorize_projection_v1b,derive_requests_v1b,authorize_requests_v1b)
    from spk_architecture_v1.memory_service_v1c import memory_service_plan_v1c,serve_projection_v1c
    trace=[]; diagnostics=[]; counts={'native_execution_memory_admissions':0,
       'native_execution_memory_projections':0,'native_execution_access_authorizations':0,
       'native_execution_memory_services':0,'native_learning_P_grants':0}
    for choice,goal in ((11,11),(11,12),(12,11),(12,12)):
        row={'choice':choice,'goal':goal}
        case=case_for(choice,goal); fabric=plan_v1a(case,'spread')
        plan=uniform_memory_plan_v1a(fabric)
        try:
            candidate_errors=[]
            admission=None
            candidates,constructor_notes=_native_service_plans(case,fabric)
            candidate_errors.extend(constructor_notes)
            for service_name,service in candidates:
                try:
                    admission=admit_memory_v1a(case,fabric,service,plan)
                    row['original_service_constructor']=service_name
                    row['original_service_object_type']=type(service).__module__+'.'+type(service).__qualname__
                    break
                except (ValueError,TypeError,KeyError,AttributeError) as ex:
                    candidate_errors.append(service_name+' ['+type(service).__name__+']:'+type(ex).__name__+':'+str(ex)[:120])
            if admission is None:
                row['candidate_errors']=candidate_errors[:100]
                raise ValueError('ORIGINAL_ADMISSION_DENIED_ALL_SERVICE_PLANS: '+'; '.join(candidate_errors[:8]))
            counts['native_execution_memory_admissions']+=1
            execution=execute_on_pes_v1b(case,fabric)
            projection=project_execution_memory_v1a(case,fabric,admission,execution)
            counts['native_execution_memory_projections']+=1
            authorized=authorize_projection_v1b(admission,projection)
            counts['native_execution_access_authorizations']+=1
            # The original memory service may have separate plan/typing
            # preconditions. A service exception is recorded, never promoted.
            try:
                original_service_plan=memory_service_plan_v1c(admission)
                service_receipt=serve_projection_v1c(admission,projection,original_service_plan)
                counts['native_execution_memory_services']+=1
                row['service_result_type']=type(service_receipt).__name__
            except (ValueError,TypeError,KeyError,AttributeError) as ex:
                row['service_diagnostic']=type(ex).__name__+':'+str(ex)[:180]
            row['admission_type']=type(admission).__name__
            row['projection_type']=type(projection).__name__
            row['access_result_type']=type(authorized).__name__
            row['original_memory_access_executed']=True
        except (ValueError,TypeError,KeyError,AttributeError) as ex:
            row['original_memory_access_executed']=False
            row['blocked_stage']=next((k for k,v in counts.items() if k!='native_learning_P_grants' and v<len(trace)+1),'unknown')
            row['diagnostic']=type(ex).__name__+':'+str(ex)[:500]
            diagnostics.append(row['diagnostic'])
        row['native_learning_P_grant']=False
        trace.append(row)
    ensure(counts['native_learning_P_grants']==0,'NATIVE_LEARNING_FABRICATION')
    return {'catalog':catalog,'original_api_attempts':len(trace),'outcomes':trace,
            'counts':counts,'diagnostics':diagnostics,
            'native_execution_memory_is_not_learning_P_authority':True,
            'frozen_components_modified':False,
            'native_learning':False,'promotion_allowed':False}

def native_policy_p_boundary(native_probe, new_runtime_receipt):
    """Do not confuse ORIGINAL execution access permissions with learning P."""
    ensure(native_probe['counts']['native_learning_P_grants']==0,'NATIVE_LEARNING_CLAIM')
    ensure(isinstance(new_runtime_receipt,dict),'INVALID_REFERENCE_RECEIPT')
    ensure(new_runtime_receipt.get('new_v1_memory_grants',0)>=0,'INVALID_GRANTS')
    return {'original_execution_access_authorizations':native_probe['counts']['native_execution_access_authorizations'],
            'new_v1_learning_P_grants':new_runtime_receipt['new_v1_memory_grants'],
            'original_learning_P_grants':0,'original_learning_P_writes':0,
            'promotion_allowed':False,'reason':'ORIGINAL_EXECUTION_ACCESS_HAS_NO_LEARNING_P_CUSTODY_TRANSFER'}
