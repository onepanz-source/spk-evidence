"""T12 v1d: execute the ORIGINAL A1d producer before ORIGINAL memory projection.

Never synthesize CLOSED, never reinterpret original memory accesses as learning P.
Source catalog and real service-plan admission come from the verified v1c bridge.
"""
from __future__ import annotations
import importlib, inspect, ast
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import ensure
from .native_bridge_v1c import (sha, pinned_source_catalog, _native_service_plans,
                                 native_policy_p_boundary)

A1D_MODULE='spk_architecture_v1.pe_fault_v1d'

class A1dUnavailable(ValueError): pass

def a1d_entrypoints(module):
    """Enumerate functions DEFINED IN frozen A1d, never imported A1b helpers."""
    functions=[]
    for name in sorted(vars(module)):
        fun=getattr(module,name)
        if (inspect.isfunction(fun) and fun.__module__==A1D_MODULE
                and not name.startswith('_') and ('execute' in name or name.startswith('run_'))):
            functions.append((name,fun))
    return sorted(functions,key=lambda x:(0 if 'fault' in x[0] or 'failstop' in x[0] else 1,x[0]))

def _invoke_a1d(fn, case, fabric, admission, service):
    """Bind only real objects that came from original executors/constructors."""
    signature=inspect.signature(fn)
    available={'case':case,'fabric':fabric,'admission':admission,
               'memory_admission':admission,'pe_admission':admission,
               'service_plan':service,'pe_service_plan':service,
               'service_admission':service}
    kwargs={}
    for name,param in signature.parameters.items():
        if param.kind in (inspect.Parameter.VAR_POSITIONAL,inspect.Parameter.VAR_KEYWORD):continue
        if name in available:kwargs[name]=available[name]
        elif param.default is inspect.Parameter.empty:
            raise A1dUnavailable('REQUIRED_ORIGINAL_PARAMETER:'+name)
    return fn(**kwargs)

def original_a1d_execution(root, case, fabric, admission, service):
    """Only ORIGINAL A1d output may be fed to projection; never wrap A1b."""
    root=Path(root).resolve(strict=True)
    source=root/'spk_architecture_v1/pe_fault_v1d.py'
    if not source.is_file() or source.is_symlink() or not source.resolve().is_relative_to(root):
        raise A1dUnavailable('ORIGINAL_A1D_SOURCE_UNAVAILABLE')
    expected=sha(source)
    # Load only after the source is confirmed to be inside the original checkout.
    module=importlib.import_module(A1D_MODULE)
    module_path=Path(inspect.getfile(module)).resolve()
    if module_path!=source.resolve() or sha(module_path)!=expected:
        raise A1dUnavailable('ORIGINAL_A1D_MODULE_PATH_OR_CONTENT_DRIFT')
    candidates=a1d_entrypoints(module)
    notes=[]
    for name,fn in candidates:
        label=A1D_MODULE+'.'+name
        try:
            result=_invoke_a1d(fn,case,fabric,admission,service)
        except (TypeError,ValueError,KeyError,AttributeError,RuntimeError) as exc:
            notes.append(label+':'+type(exc).__name__+':'+str(exc)[:160]);continue
        if not isinstance(result,dict) or result.get('status') not in ('CLOSED','PE_FAULT'):
            notes.append(label+':NOT_A1D_STATUS_'+str(result.get('status') if isinstance(result,dict) else type(result).__name__))
            continue
        payload=result.get('result') if result['status']=='CLOSED' else result.get('committed_prefix')
        if not isinstance(payload,dict) or not isinstance(payload.get('observations'),dict):
            notes.append(label+':MISSING_A1D_OBSERVATIONS');continue
        if not isinstance(payload['observations'].get('batches'),list) or not isinstance(payload['observations'].get('routes'),list):
            notes.append(label+':MISSING_A1D_BATCHES_OR_ROUTES');continue
        return result,{'producer':label,'source_sha256':expected,'status':result['status'],
                       'processed_batches':payload.get('processed_batches'),
                       'processed_events':payload.get('processed_events')}
    candidates_txt=[{'name':name,'args':list(inspect.signature(fun).parameters)} for name,fun in candidates]
    raise A1dUnavailable('NO_VALID_ORIGINAL_A1D_RESULT:'+repr({'candidates':candidates_txt,'attempts':notes})[:2000])

def original_native_execution_probe(root):
    """Four authentic A/B/C cases; count stages independently and a *complete row*."""
    catalog=pinned_source_catalog(root)
    from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import case_for
    from spk_architecture_v1.pe_fabric_v1a import plan_v1a
    from spk_architecture_v1.memory_projection_v1a import (uniform_memory_plan_v1a,
                           admit_memory_v1a,project_execution_memory_v1a)
    from spk_architecture_v1.memory_access_v1b import authorize_projection_v1b
    from spk_architecture_v1.memory_service_v1c import memory_service_plan_v1c,serve_projection_v1c
    counts={'native_execution_memory_admissions':0,'native_A1d_executions':0,
            'native_execution_memory_projections':0,'native_execution_access_authorizations':0,
            'native_execution_memory_services':0,'completed_original_memory_chains':0,
            'native_learning_P_grants':0}
    trace=[];diagnostics=[]
    for choice,goal in ((11,11),(11,12),(12,11),(12,12)):
        row={'choice':choice,'goal':goal,'original_memory_access_executed':False}
        case=case_for(choice,goal);fabric=plan_v1a(case,'spread'); plan=uniform_memory_plan_v1a(fabric)
        stage='original_service_admission'
        try:
            candidates,ctor_notes=_native_service_plans(case,fabric)
            errors=list(ctor_notes)
            admission=service_used=None
            for label,service in candidates:
                try:
                    admission=admit_memory_v1a(case,fabric,service,plan)
                    service_used=service
                    row['original_service_constructor']=label
                    row['original_service_object_type']=type(service).__module__+'.'+type(service).__qualname__
                    break
                except (ValueError,TypeError,KeyError,AttributeError) as exc:
                    errors.append(label+':'+type(exc).__name__+':'+str(exc)[:160])
            if admission is None:
                row['candidate_errors']=errors[:30]
                raise A1dUnavailable('ORIGINAL_ADMISSION_DENIED_ALL_PLANS:'+repr(errors[:5]))
            counts['native_execution_memory_admissions']+=1
            stage='original_A1d_execution'
            execution,origin=original_a1d_execution(root,case,fabric,admission,service_used)
            row['A1d_provenance']=origin
            counts['native_A1d_executions']+=1
            stage='original_memory_projection'
            projection=project_execution_memory_v1a(case,fabric,admission,execution)
            counts['native_execution_memory_projections']+=1
            stage='original_memory_access_authorization'
            authority=authorize_projection_v1b(admission,projection)
            counts['native_execution_access_authorizations']+=1
            row['admission_type']=type(admission).__name__
            row['projection_schema']=projection.get('schema')
            row['projection_status']=projection.get('status')
            row['authority_result_type']=type(authority).__name__
            stage='original_memory_service'
            try:
                service_plan=memory_service_plan_v1c(admission)
                receipt=serve_projection_v1c(admission,projection,service_plan)
                counts['native_execution_memory_services']+=1
                row['memory_service_result_type']=type(receipt).__name__
            except (ValueError,TypeError,KeyError,AttributeError) as exc:
                row['service_diagnostic']=type(exc).__name__+':'+str(exc)[:250]
            counts['completed_original_memory_chains']+=1
            row['original_memory_access_executed']=True
        except (ValueError,TypeError,KeyError,AttributeError,RuntimeError) as exc:
            row['blocked_stage']=stage
            row['diagnostic']=type(exc).__name__+':'+str(exc)[:2400]
            diagnostics.append(row['diagnostic'])
        row['native_learning_P_grant']=False
        trace.append(row)
    ensure(counts['native_learning_P_grants']==0,'NATIVE_LEARNING_FABRICATION')
    return {'catalog':catalog,'original_api_attempts':len(trace),'outcomes':trace,
            'counts':counts,'diagnostics':diagnostics,
            'native_execution_memory_is_not_learning_P_authority':True,
            'native_A1d_producer_required':True,'frozen_components_modified':False,
            'native_learning':False,'promotion_allowed':False}
